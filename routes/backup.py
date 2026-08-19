# registrofacil/routes/backup.py
from flask import Blueprint, request, jsonify, session, send_file, url_for, flash, redirect, render_template
import os
import shutil
import sqlite3
from datetime import datetime
import functools
import zipfile 
from io import BytesIO 
import time 
import socket

import tempfile 
import secrets 
import gc 

# Importações de outros módulos
from routes.auth import login_status_required, admin_required, verificar_csrf_token, get_client_ip, gerar_csrf_token
from routes.permissoes import permission_required
from models import (
    gravar_log, DATABASE_PATH, get_backup_config, get_upload_folder,
    list_users_presence, summarize_presence,
)
from config import Config 
from data.system_updates import begin_restore_maintenance, end_restore_maintenance
from utils.logger import logger
from utils.backup_service import (
    BACKUP_PREFIX,
    create_backup_archive,
    validate_backup_archive,
    write_backup_status,
    read_backup_status,
    apply_retention,
    apply_rollback_retention,
    stage_backup_restore,
    promote_staged_restore,
    rollback_promoted_restore,
)

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

def create_temp_db_backup(target_dir: str) -> str: 
    """Cria uma cópia temporária do banco de dados para backup em um diretório temporário do sistema."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    db_temp_file = f"registrofacil_temp_db_{timestamp}_{secrets.token_hex(4)}.db" 

    temp_dir_for_db = Config.TEMP_DIR
    db_temp_path = os.path.join(temp_dir_for_db, db_temp_file) 
    
    conn = None
    dest_conn = None

    try:
        logger.info(f"Iniciando backup do banco de dados para temporário do sistema (manual): {db_temp_path}")
        conn = sqlite3.connect(DATABASE_PATH, timeout=30)
        dest_conn = sqlite3.connect(db_temp_path) 
        conn.backup(dest_conn)
        dest_conn.close()
        conn.close()
        del dest_conn
        del conn
        gc.collect() 
        time.sleep(0.1) 
        
        if not os.path.exists(db_temp_path) or os.path.getsize(db_temp_path) == 0:
            raise Exception(f"Backup do banco de dados resultou em arquivo vazio em {db_temp_path}")
        
        return db_temp_path
    except Exception as e:
        if dest_conn: dest_conn.close()
        if conn: conn.close()
        if os.path.exists(db_temp_path):
            try:
                os.remove(db_temp_path)
            except OSError as exc:
                logger.error(f"Falha ao remover arquivo temporário parcial do DB {db_temp_path}: {exc}")
        raise Exception(f"Falha no backup do banco de dados: {str(e)}")


def add_folder_to_zip(zipf: zipfile.ZipFile, source: str, arcname: str) -> int:
    """Adiciona um diretório ao arquivo ZIP."""
    logger.info(f"Verificando diretório para backup: {source}")
    if not os.path.exists(source):
        logger.error(f"DIRETÓRIO CRÍTICO NÃO ENCONTRADO PARA BACKUP: {source}.")
        return 0
    if not os.path.isdir(source):
        logger.error(f"CAMINHO NÃO É UM DIRETÓRIO PARA BACKUP: {source}.")
        return 0
    
    count = 0
    for root, _, files in os.walk(source):
        for file in files:
            try:
                file_path = os.path.join(root, file)
                if file.startswith(('temp_db_', 'permission_test_', '.test_write_')):
                    continue
                arc_path = os.path.join(arcname, os.path.relpath(file_path, source))
                zipf.write(file_path, arc_path)
                count += 1
            except Exception as e:
                logger.error(f"Erro ao adicionar arquivo '{file_path}' ao ZIP: {str(e)}")
    logger.info(f"Conteúdo de {source} ({count} arquivos) adicionado ao backup.")
    return count

def get_machine_ip():
    """Obtém o IP da máquina local."""
    try:
        # Cria uma conexão UDP temporária para obter o IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            # Fallback: usa o hostname
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

@backup_bp.route('/', methods=['GET'])
@login_status_required
@permission_required('backup_visualizar')
def index():
    backups_list = []
    backup_config = get_backup_config()
    local_backup_root = backup_config.get('local_path', Config.BACKUP_ROOT_DIR)
    backup_status = read_backup_status(local_backup_root)

    try:
        os.makedirs(local_backup_root, exist_ok=True) 
        if os.path.exists(local_backup_root):
            for filename in sorted(os.listdir(local_backup_root), reverse=True):
                # Aceita tanto o padrão novo quanto os antigos para listagem
                if filename.endswith(".zip") and (filename.startswith("registrofacil_bkp_") or filename.startswith("registrofacil_manual_backup_") or filename.startswith("registrofacil_scheduled_backup_")):
                    file_path = os.path.join(local_backup_root, filename)
                    if os.path.isfile(file_path):
                        # Tenta extrair a data do nome do arquivo
                        timestamp_str = filename.replace("registrofacil_bkp_", "").replace("registrofacil_manual_backup_", "").replace("registrofacil_scheduled_backup_", "").replace(".zip", "")
                        try:
                            created_at = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                            date_display = created_at.strftime('%d/%m/%Y %H:%M:%S')
                        except ValueError:
                            date_display = 'Data desconhecida'
                        
                        file_size = os.path.getsize(file_path)
                        backups_list.append({
                            'name': filename,
                            'created_at': date_display,
                            'size': f"{file_size / (1024 * 1024):.2f} MB" if file_size > 0 else "0 KB",
                            'download_url': url_for('backup.download_backup', filename=filename)
                        })
    except Exception as e:
        logger.error(f"Erro ao listar arquivos de backup: {e}", exc_info=True)
        flash("Erro ao carregar lista de backups.", 'danger')

    # Obter informações do sistema
    machine_ip = get_machine_ip()
    has_database = os.path.exists(DATABASE_PATH)
    is_server = has_database  # Se tem o banco, é considerado servidor
    
    csrf_token_val = gerar_csrf_token()
    db_config = {'path_completo': DATABASE_PATH}
    backup_config = get_backup_config()
    return render_template('backup.html',
                         backups=backups_list, 
                         csrf_token=csrf_token_val, 
                         config=Config,
                         machine_ip=machine_ip,
                         has_database=has_database,
                         is_server=is_server,
                         db_config=db_config,
                         backup_config=backup_config,
                         DEFAULT_BACKUP_PATH=Config.DEFAULT_BACKUP_PATH,
                         UPLOAD_PROCESSOS_DIR=Config.UPLOAD_PROCESSOS_DIR,
                         backup_status=backup_status)


@backup_bp.route('/presence/heartbeat', methods=['POST'])
@login_status_required
def presence_heartbeat():
    """Registra atividade da sessão atual sem expor dados de outros usuários."""
    if not verificar_csrf_token(request.headers.get('X-CSRFToken') or request.form.get('csrf_token')):
        return jsonify(success=False, message='Token de segurança inválido.', type='danger'), 400
    return jsonify(success=True)


@backup_bp.route('/users-presence', methods=['GET'])
@login_status_required
@admin_required
def users_presence():
    """Retorna a presença operacional dos usuários para administradores."""
    users = list_users_presence()
    return jsonify(
        success=True,
        users=users,
        summary=summarize_presence(users),
        online_window_seconds=120,
        server_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )


@backup_bp.route('/manual', methods=['POST'])
@login_status_required
@permission_required('backup_criar')
def manual_backup():
    if not verificar_csrf_token(request.form.get('csrf_token')):
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403

    try:
        backup_config = get_backup_config()
        local_backup_root = backup_config.get('local_path', Config.BACKUP_ROOT_DIR)
        result = create_backup_archive(
            destination_dir=local_backup_root,
            database_path=DATABASE_PATH,
            upload_processos=get_upload_folder(),
            upload_empresa=Config.EMPRESA_UPLOAD_FOLDER,
            log_dir=Config.LOG_DIR,
            source="manual",
        )
        validate_backup_archive(result["path"])
        apply_retention(local_backup_root)
        write_backup_status(local_backup_root, status="success_local", source="manual", result=result)
        gravar_log(
            "Backup Manual", None, session.get('usuario_id'), get_client_ip(),
            f"Backup unificado gerado: {result['filename']} | SHA-256: {result['sha256']}",
        )
        return jsonify(
            success=True,
            message=f"Backup '{result['filename']}' gerado e verificado com sucesso!",
            download_url=url_for('backup.download_backup', filename=result['filename']),
            filename=result['filename'],
            sha256=result['sha256'],
            size=result['size'],
            type='success',
        ), 200

    except Exception as e:
        logger.exception(f"Erro ao criar backup manual: {e}")
        try:
            write_backup_status(locals().get('local_backup_root', Config.BACKUP_ROOT_DIR), status="failed", source="manual", error=str(e))
        except Exception:
            logger.warning("Falha ao persistir status de erro do backup manual.", exc_info=True)
        return jsonify(success=False, message=f"Erro ao criar backup: {e}", type='danger'), 500

@backup_bp.route('/restore', methods=['POST'])
@login_status_required
@admin_required
def restore_backup():
    """Restaura um backup completo após pré-backup e validação em staging."""
    if not verificar_csrf_token(request.form.get('csrf_token')):
        flash("Token de segurança inválido.", 'danger')
        return redirect(url_for('backup.index'))

    backup_config = get_backup_config()
    local_backup_root = os.path.abspath(backup_config.get('local_path', Config.BACKUP_ROOT_DIR))
    filename = os.path.basename((request.form.get('filename') or '').strip())
    if not filename.startswith(BACKUP_PREFIX) or not filename.endswith('.zip') or filename != (request.form.get('filename') or '').strip():
        flash("Nome de backup inválido.", 'danger')
        return redirect(url_for('backup.index'))
    archive_path = os.path.abspath(os.path.join(local_backup_root, filename))
    if os.path.commonpath([local_backup_root, archive_path]) != local_backup_root or not os.path.isfile(archive_path):
        flash("Backup selecionado não foi encontrado.", 'danger')
        return redirect(url_for('backup.index'))

    maintenance_started = False
    promoted = None
    try:
        validate_backup_archive(archive_path)
        pre_restore = create_backup_archive(
            destination_dir=local_backup_root,
            database_path=DATABASE_PATH,
            upload_processos=get_upload_folder(),
            upload_empresa=Config.EMPRESA_UPLOAD_FOLDER,
            log_dir=Config.LOG_DIR,
            source="pre_restore",
        )
        staged = stage_backup_restore(archive_path)
        begin_restore_maintenance()
        maintenance_started = True
        promoted = promote_staged_restore(
            staged,
            database_path=DATABASE_PATH,
            upload_processos=get_upload_folder(),
            upload_empresa=Config.EMPRESA_UPLOAD_FOLDER,
            rollback_root=os.path.join(Config.DATA_DIR, 'restore_rollbacks'),
            preserve_keys=True,
        )
        from models import init_db, rebuild_fts_index, test_db_connection
        init_db()
        rebuild_fts_index()
        if not test_db_connection():
            raise RuntimeError("O health check do banco restaurado falhou.")
        apply_rollback_retention(os.path.join(Config.DATA_DIR, 'restore_rollbacks'))
        end_restore_maintenance()
        maintenance_started = False
        write_backup_status(local_backup_root, status="restore_success", source="restore", result={"filename": filename, "sha256": staged["sha256"], "size": os.path.getsize(archive_path)})
        gravar_log(
            "Restauração de backup", None, session.get('usuario_id'), get_client_ip(),
            f"{filename} restaurado. Pré-backup: {pre_restore['filename']}. Rollback: {promoted['rollback_dir']}"
        )
        flash(
            f"Backup '{filename}' restaurado com sucesso. As chaves da instalação foram preservadas. "
            f"Pré-backup: {pre_restore['filename']}",
            'success',
        )
    except Exception as e:
        logger.exception("Erro ao restaurar backup: %s", e)
        if promoted:
            try:
                rollback_promoted_restore(
                    promoted['rollback_dir'],
                    database_path=DATABASE_PATH,
                    upload_processos=get_upload_folder(),
                    upload_empresa=Config.EMPRESA_UPLOAD_FOLDER,
                )
                logger.warning("Restauração revertida automaticamente após falha no health check.")
            except Exception:
                logger.critical("Falha ao reverter restauração após erro.", exc_info=True)
        if maintenance_started:
            end_restore_maintenance()
        write_backup_status(local_backup_root, status="restore_failed", source="restore", error=str(e))
        flash(f"Restauração não concluída: {e}", 'danger')
    return redirect(url_for('backup.index'))


@backup_bp.route('/download/<filename>', methods=['GET'], endpoint='download_backup')
@login_status_required
@permission_required('backup_download')
def download_backup(filename):
    backup_config = get_backup_config()
    local_backup_root = backup_config.get('local_path', Config.BACKUP_ROOT_DIR)
    
    # Sanitização básica do nome do arquivo
    if ".." in filename or "/" in filename or "\\" in filename:
        flash("Nome de arquivo inválido.", 'danger')
        return redirect(url_for('backup.index'))
        
    file_path = os.path.join(local_backup_root, filename) 
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_file(file_path, as_attachment=True)
    
    flash("Arquivo de backup não encontrado.", 'danger')
    return redirect(url_for('backup.index'))

@backup_bp.route('/delete/<filename>', methods=['POST'])
@login_status_required
@permission_required('backup_excluir')
def delete_backup(filename):
    if not verificar_csrf_token(request.form.get('csrf_token')):
        flash("Token de segurança inválido.", 'danger')
        return redirect(url_for('backup.index'))

    backup_config = get_backup_config()
    local_backup_root = backup_config.get('local_path', Config.BACKUP_ROOT_DIR)
    
    if ".." in filename or "/" in filename or "\\" in filename:
        flash("Nome de arquivo inválido.", 'danger')
        return redirect(url_for('backup.index'))

    file_path = os.path.join(local_backup_root, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            gravar_log("Excluiu Backup", None, session.get('usuario_id'), get_client_ip(), f"Arquivo: {filename}")
            flash(f"Backup '{filename}' excluído com sucesso.", 'success')
        else:
            flash("Arquivo não encontrado.", 'warning')
    except Exception as e:
        logger.error(f"Erro ao excluir backup {filename}: {e}")
        flash("Erro ao excluir o arquivo de backup.", 'danger')
    
    return redirect(url_for('backup.index'))


@backup_bp.route('/test-db', methods=['POST'])
@login_status_required
@admin_required
def test_db():
    """Testa conexão com banco de dados e redireciona de volta ao backup."""
    if not verificar_csrf_token(request.form.get('csrf_token')):
        flash("Token de segurança inválido.", 'danger')
        return redirect(url_for('backup.index'))
    try:
        from models import test_db_connection
        if test_db_connection():
            flash("Conexão com o banco de dados está funcional!", 'success')
        else:
            flash("Erro ao conectar com o banco de dados.", 'danger')
    except Exception as e:
        flash(f"Erro ao testar banco de dados: {str(e)}", 'danger')
    return redirect(url_for('backup.index'))


@backup_bp.route('/optimize-db', methods=['POST'])
@login_status_required
@admin_required
def optimize_db():
    """Otimiza banco de dados e redireciona de volta ao backup."""
    if not verificar_csrf_token(request.form.get('csrf_token')):
        flash("Token de segurança inválido.", 'danger')
        return redirect(url_for('backup.index'))
    try:
        from models import optimize_database
        if optimize_database():
            flash("Banco de dados otimizado com sucesso! O arquivo foi desfragmentado e reorganizado.", 'success')
            gravar_log("Otimizou banco de dados", None, session.get('usuario_id'), get_client_ip(), "Comando VACUUM executado")
        else:
            flash("Erro ao otimizar o banco de dados. Verifique os logs.", 'danger')
    except Exception as e:
        flash(f"Erro ao otimizar banco de dados: {str(e)}", 'danger')
    return redirect(url_for('backup.index'))


@backup_bp.route('/repair-db', methods=['POST'])
@login_status_required
@admin_required
def repair_db():
    """
    Verifica a integridade do banco de dados e tenta reparar corrupção
    usando REINDEX + VACUUM. Redireciona de volta ao backup com mensagem detalhada.
    """
    if not verificar_csrf_token(request.form.get('csrf_token')):
        flash("Token de segurança inválido.", 'danger')
        return redirect(url_for('backup.index'))
    try:
        from models import check_and_repair_database
        result = check_and_repair_database()

        if result.get('error') and not result.get('repaired'):
            flash(
                f"Erro fatal ao acessar o banco de dados: {result['error']}. "
                "O arquivo pode estar severamente corrompido. Use Reconstruir BD.",
                'danger'
            )
        elif result.get('ok') and not result.get('repaired'):
            flash(
                "✔ Banco de dados verificado — nenhum problema encontrado.",
                'success'
            )
        elif result.get('ok') and result.get('repaired'):
            flash(
                "✔ Banco de dados reparado com sucesso! "
                "REINDEX e VACUUM foram executados e a integridade foi restaurada. "
                "Recomenda-se gerar um novo backup agora.",
                'success'
            )
            gravar_log(
                "Reparou banco de dados", None,
                session.get('usuario_id'), get_client_ip(),
                "REINDEX + VACUUM executados — integridade restaurada"
            )
        else:
            details_str = ' | '.join(result.get('details', []))
            flash(
                f"⚠ Reparo executado mas o banco ainda apresenta problemas. "
                f"Use a opção Reconstruir BD para recuperação completa. "
                f"Detalhes: {details_str[:200]}",
                'warning'
            )
    except Exception as e:
        logger.exception(f"Erro ao executar reparo do banco de dados: {e}")
        flash(f"Erro inesperado durante o reparo: {str(e)}", 'danger')
    return redirect(url_for('backup.index'))


@backup_bp.route('/reconstruct-db', methods=['POST'])
@login_status_required
@admin_required
def reconstruct_db():
    """
    Reconstrução nuclear do banco via iterdump().
    Lê dado a dado ignorando páginas corrompidas e cria um banco novo.
    Usa quando VACUUM/REINDEX não resolvem o erro 'database disk image is malformed'.
    """
    if not verificar_csrf_token(request.form.get('csrf_token')):
        flash("Token de segurança inválido.", 'danger')
        return redirect(url_for('backup.index'))
    try:
        from models import reconstruct_database
        result = reconstruct_database()

        if result.get('ok'):
            # Recriar tabelas ausentes e FTS após reconstrução
            try:
                from models import init_db, rebuild_fts_index
                init_db()
                rebuild_fts_index()
                logger.info("Esquema e FTS recriados com sucesso após reconstrução.")
            except Exception as post_e:
                logger.warning(f"Aviso pós-reconstrução: {post_e}")

            backup_info = f" Backup do banco original salvo em: {os.path.basename(result['backup_path'])}." if result.get('backup_path') else ""
            flash(
                f"✔ Banco de dados reconstruído com sucesso! "
                f"{result['rows_recovered']} instruções recuperadas, "
                f"{result['rows_skipped']} ignoradas por corrupção.{backup_info} "
                "O sistema está funcionando com o banco reconstruído. "
                "Gere um novo backup agora.",
                'success'
            )
            gravar_log(
                "Reconstruiu banco de dados", None,
                session.get('usuario_id'), get_client_ip(),
                f"iterdump: {result['rows_recovered']} recuperadas, {result['rows_skipped']} ignoradas"
            )
        else:
            details_str = ' | '.join(result.get('details', []))
            flash(
                f"✘ Falha na reconstrução do banco: {result.get('error', 'Erro desconhecido')}. "
                f"Detalhes: {details_str[:300]}. "
                "Restaure um backup salvo anteriormente.",
                'danger'
            )
    except Exception as e:
        logger.exception(f"Erro ao reconstruir banco de dados: {e}")
        flash(f"Erro inesperado durante a reconstrução: {str(e)}", 'danger')
    return redirect(url_for('backup.index'))


@backup_bp.route('/rebuild-fts', methods=['POST'])
@login_status_required
@admin_required
def rebuild_fts():
    """
    Reconstrói o índice FTS5 (Full-Text Search) do zero.
    Solução direta para o erro 'database disk image is malformed' causado
    por corrupção nas shadow tables do FTS5, que dispara via trigger no UPDATE de processos.
    """
    if not verificar_csrf_token(request.form.get('csrf_token')):
        flash("Token de segurança inválido.", 'danger')
        return redirect(url_for('backup.index'))
    try:
        from models import rebuild_fts_index
        ok = rebuild_fts_index()
        if ok:
            flash(
                "✔ Índice de busca (FTS5) reconstruído com sucesso! "
                "O erro 'database disk image is malformed' na edição de processos foi corrigido. "
                "Você já pode editar processos normalmente.",
                'success'
            )
            gravar_log(
                "Reconstruiu índice FTS5", None,
                session.get('usuario_id'), get_client_ip(),
                "Índice processos_fts reconstruído — triggers corrigidos"
            )
        else:
            flash(
                "✘ Falha ao reconstruir o índice FTS5. Verifique os logs do sistema.",
                'danger'
            )
    except Exception as e:
        logger.exception(f"Erro ao reconstruir FTS5: {e}")
        flash(f"Erro inesperado ao reconstruir índice: {str(e)}", 'danger')
    return redirect(url_for('backup.index'))
