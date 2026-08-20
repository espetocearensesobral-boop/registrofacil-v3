# registrofacil/routes/configuracoes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
import os
import secrets
from datetime import datetime

from routes.auth import login_status_required, admin_required, verificar_csrf_token, get_client_ip, gerar_csrf_token
from routes.permissoes import permission_required, has_permission
from models import (
    get_email_config, save_email_config, send_email,
    get_backup_config, save_backup_config,
    executar_query, gravar_log, obter_status_processo_config, obter_tipos_servico,
    update_status_processo, update_tipo_servico,
    add_status_processo, add_tipo_servico,
    toggle_status_processo, toggle_tipo_servico
)
from config import Config
from utils.logger import sistema_logger as logger
from utils.scheduler import configure_and_start_scheduler
from utils.sftp_backup import test_sftp_connection

configuracoes_bp = Blueprint('configuracoes', __name__, url_prefix='/configuracoes')

def proteger_input(texto):
    if texto is None:
        return ""
    return str(texto).strip()

@configuracoes_bp.route('/', methods=['GET', 'POST'])
@configuracoes_bp.route('/salvar', methods=['GET', 'POST'])
@login_status_required
@permission_required('config_geral')
def index():
    usuario_id = session.get('usuario_id')
    usuario_role = session.get('usuario_role')
    active_tab = request.args.get('tab', 'status')
    pode_ver_atividades = usuario_role in {'admin', 'suporte'} or has_permission(usuario_id, 'atividades_visualizar')

    if request.method == 'GET' and active_tab == 'backup':
        return redirect(url_for('backup.index', config='1'))

    if request.method == 'POST':
        # Verifica se é uma requisição AJAX (para e-mail)
        is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest') or \
                 (request.form.get('test_email') == '1') or \
                 (request.form.get('action') == 'update_email_config')

        if not verificar_csrf_token(request.form.get('csrf_token')):
            msg = "Token de segurança inválido. Por favor, tente novamente."
            if is_ajax:
                return jsonify({'success': False, 'message': msg})
            flash(msg, 'danger')
            return redirect(url_for('configuracoes.index', tab=active_tab))

        action = request.form.get('action')
        
        try:
            if action == 'update_db_settings':
                active_tab = 'db'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                
                # Simulação de teste de conexão para a aba de banco de dados
                from models import test_db_connection
                if test_db_connection():
                    flash("Conexão com o banco de dados está funcional!", 'success')
                else:
                    flash("Erro ao conectar com o banco de dados.", 'danger')
            
            elif action == 'optimize_db':
                active_tab = 'db'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                
                # Otimizar banco de dados usando VACUUM
                from models import optimize_database
                try:
                    if optimize_database():
                        flash("Banco de dados otimizado com sucesso! O arquivo foi desfragmentado e reorganizado.", 'success')
                        gravar_log("Otimizou banco de dados", None, usuario_id, get_client_ip(), "Banco de dados otimizado (VACUUM)", contexto="Comando VACUUM executado pelo administrador")
                    else:
                        flash("Erro ao otimizar o banco de dados. Verifique os logs.", 'danger')
                except Exception as e:
                    logger.error(f"Erro ao otimizar banco de dados: {e}")
                    flash(f"Erro ao otimizar banco de dados: {str(e)}", 'danger')

            elif action == 'update_email_config':
                active_tab = 'email'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                
                # Mapeamento de campos para coincidir com o template
                smtp_host = proteger_input(request.form.get('mail_server'))
                smtp_port_raw = request.form.get('mail_port')
                smtp_port = int(smtp_port_raw) if smtp_port_raw and smtp_port_raw.isdigit() else 587
                smtp_username = proteger_input(request.form.get('mail_username'))
                smtp_password = request.form.get('mail_password')
                sender_email = proteger_input(request.form.get('mail_default_sender'))
                sender_name = "Registro Fácil"
                
                use_tls = 1 if request.form.get('mail_use_tls') == '1' else 0
                use_ssl = 1 if request.form.get('mail_use_ssl') == '1' else 0
                if use_tls and use_ssl:
                    raise ValueError("Escolha apenas uma opção de segurança: TLS ou SSL.")
                smtp_encryption = 'tls' if use_tls else ('ssl' if use_ssl else 'none')

                ativo = 1 if request.form.get('ativo') in ['1', 'on'] else 0
                notify_password_recovery = 1 if request.form.get('notify_password_recovery') in ['1', 'on'] else 0
                notify_deadlines = 1 if request.form.get('notify_deadlines') in ['1', 'on'] else 0
                notify_backup_failures = 1 if request.form.get('notify_backup_failures') in ['1', 'on'] else 0
                notify_security_events = 1 if request.form.get('notify_security_events') in ['1', 'on'] else 0
                config_id_raw = request.form.get('id')
                config_id = int(config_id_raw) if config_id_raw and config_id_raw.isdigit() else None

                if not all([smtp_host, smtp_username, sender_email]):
                    raise ValueError("Todos os campos obrigatórios de e-mail devem ser preenchidos.")
                
                # Validar formato de e-mail
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, sender_email):
                    raise ValueError("O e-mail do remetente não é válido.")

                email_data = {
                    'id': config_id,
                    'smtp_host': smtp_host,
                    'smtp_port': smtp_port,
                    'smtp_encryption': smtp_encryption,
                    'smtp_username': smtp_username,
                    'smtp_password': smtp_password,
                    'sender_email': sender_email,
                    'sender_name': sender_name,
                    'ativo': ativo,
                    'notify_password_recovery': notify_password_recovery,
                    'notify_deadlines': notify_deadlines,
                    'notify_backup_failures': notify_backup_failures,
                    'notify_security_events': notify_security_events,
                }

                # Teste SMTP sem gravar: usa os valores atuais do formulário e envia
                # uma mensagem consolidada com as políticas de notificação marcadas.
                if request.form.get('test_email') == '1':
                    stored_email_config = get_email_config()
                    test_password = smtp_password or stored_email_config.get('smtp_password', '')
                    if not test_password:
                        raise ValueError("Informe a senha SMTP para executar o teste.")

                    notification_tests = []
                    if notify_password_recovery:
                        notification_tests.append("Recuperação de acesso")
                    if notify_deadlines:
                        notification_tests.append("Prazos de processos")
                    if notify_backup_failures:
                        notification_tests.append("Falhas de backup")
                    if notify_security_events:
                        notification_tests.append("Eventos de segurança")
                    notification_summary = (
                        "\\n".join(f"- {item}: habilitado para teste" for item in notification_tests)
                        if notification_tests else "- Nenhuma notificação automática habilitada"
                    )
                    test_body = f"""Teste de configuração de e-mail — Registro Fácil

Este é um teste de conectividade SMTP. Se esta mensagem foi recebida, o servidor, a porta, a autenticação e a criptografia foram aceitos.

Políticas de notificação selecionadas:
{notification_summary}

O teste não cria processos, não dispara backup e não altera a senha de nenhum usuário. Ele apenas valida o envio e apresenta as políticas selecionadas."""
                    test_email_config = {
                        **email_data,
                        'smtp_password': test_password,
                        'ativo': 1,
                    }
                    success, message = send_email(
                        to_address=sender_email,
                        subject="Teste SMTP e notificações - Registro Fácil",
                        body=test_body,
                        sender_name=sender_name,
                        sender_email=sender_email,
                        app_instance=current_app._get_current_object(),
                        email_config_override=test_email_config,
                    )
                    if success:
                        message = f"Teste enviado para {sender_email}. Políticas incluídas: {len(notification_tests)}."
                    return jsonify({'success': success, 'message': message})

                # Se não houver ID, é uma nova configuração
                is_new = config_id is None or config_id <= 0
                if save_email_config(email_data, is_new_config=is_new):
                    gravar_log("Configurações de e-mail atualizadas", None, usuario_id, get_client_ip(),
                        f"Servidor SMTP: {smtp_host} | Remetente: {sender_email}",
                        contexto=f"Host: {smtp_host}\nPorta: {smtp_port}\nE-mail: {sender_email}\nCriptografia: {smtp_encryption}\nAtivo: {'Sim' if ativo else 'Não'}")
                    return jsonify({'success': True, 'message': "Configurações de e-mail salvas com sucesso!"})
                else:
                    raise ValueError("Falha ao salvar as configurações de e-mail no banco de dados.")
            
            elif action == 'test_sftp_connection':
                active_tab = 'backup'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                current_backup = get_backup_config()
                sftp_config = {
                    **current_backup,
                    'cloud_provider': 'sftp',
                    'sftp_host': proteger_input(request.form.get('sftp_host')),
                    'sftp_port': request.form.get('sftp_port') or 22,
                    'sftp_username': proteger_input(request.form.get('sftp_username')),
                    'sftp_password': request.form.get('sftp_password') or current_backup.get('sftp_password', ''),
                    'sftp_remote_path': proteger_input(request.form.get('sftp_remote_path') or '/backups/'),
                }
                result = test_sftp_connection(sftp_config)
                flash(result['message'], 'success')

            elif action == 'update_backup_settings':
                active_tab = 'backup'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                
                local_path = proteger_input(request.form.get('local_path'))
                uploads_path = None  # Caminho de anexos é gerenciado pelo Config, não pelo formulário
                auto_backup_enabled = 1 if request.form.get('auto_backup_enabled') in ['on', '1', 'true', True] else 0
                backup_frequency = proteger_input(request.form.get('backup_frequency'))
                backup_time = proteger_input(request.form.get('backup_time'))
                backup_days = request.form.getlist('backup_days[]')
                backup_day_of_month_raw = request.form.get('backup_day_of_month')
                backup_day_of_month = int(backup_day_of_month_raw) if backup_day_of_month_raw and backup_day_of_month_raw.isdigit() else 1
                cloud_provider = proteger_input(request.form.get('cloud_provider') or 'none').lower()
                if cloud_provider not in {'none', 'sftp'}:
                    raise ValueError("Provedor remoto inválido.")
                sftp_host = proteger_input(request.form.get('sftp_host'))
                sftp_port_raw = request.form.get('sftp_port') or '22'
                sftp_username = proteger_input(request.form.get('sftp_username'))
                sftp_password = request.form.get('sftp_password') or ''
                sftp_remote_path = proteger_input(request.form.get('sftp_remote_path') or '/backups/')
                try:
                    sftp_port = int(sftp_port_raw)
                except ValueError:
                    raise ValueError("A porta SFTP precisa ser numérica.")
                if not 1 <= sftp_port <= 65535:
                    raise ValueError("A porta SFTP deve estar entre 1 e 65535.")
                if cloud_provider == 'sftp' and not all([sftp_host, sftp_username, sftp_remote_path]):
                    raise ValueError("Host, usuário e caminho remoto são obrigatórios para SFTP.")

                if not local_path:
                    raise ValueError("O caminho local para o backup é obrigatório.")
                
                try:
                    os.makedirs(local_path, exist_ok=True)
                    test_file = os.path.join(local_path, f".test_{secrets.token_hex(4)}")
                    with open(test_file, 'w') as f: f.write("test")
                    os.remove(test_file)
                except Exception as e:
                    raise ValueError(f"Erro de permissão no caminho de backup: {e}")

                backup_config_data = {
                    'id': int(request.form.get('id')) if request.form.get('id') else None,
                    'local_path': local_path,
                    'uploads_path': uploads_path,
                    'auto_backup_enabled': auto_backup_enabled,
                    'backup_frequency': backup_frequency,
                    'backup_time': backup_time,
                    'backup_days': backup_days,
                    'backup_day_of_month': backup_day_of_month,
                    'cloud_provider': cloud_provider,
                    'sftp_host': sftp_host,
                    'sftp_port': sftp_port,
                    'sftp_username': sftp_username,
                    'sftp_password': sftp_password,
                    'sftp_remote_path': sftp_remote_path,
                }

                if save_backup_config(backup_config_data):
                    try:
                        configure_and_start_scheduler(current_app.app_context)
                        flash("Configurações de backup atualizadas com sucesso!", 'success')
                    except Exception as e:
                        logger.error(f"Erro ao reconfigurar scheduler: {e}")
                        flash("Configurações salvas, mas houve um erro no agendador.", 'warning')
                    gravar_log("Configurações de backup atualizadas", None, usuario_id, get_client_ip(),
                    f"Tipo: {backup_frequency} | Auto: {'Ativado' if auto_backup_enabled else 'Desativado'} | Hora: {backup_time}",
                    contexto=f"Frequência: {backup_frequency}\nAuto-backup: {'Ativado' if auto_backup_enabled else 'Desativado'}\nHorário: {backup_time}\nCaminho: {local_path}")

            elif action == 'add_status':
                active_tab = 'status'
                nome = proteger_input(request.form.get('nome'))
                hex_color = proteger_input(request.form.get('hex_color'))
                if not nome or not hex_color:
                    raise ValueError("Nome e cor são obrigatórios.")
                add_status_processo(nome, hex_color)
                flash(f"Status '{nome}' adicionado com sucesso!", 'success')
                gravar_log("Status adicionado", None, usuario_id, get_client_ip(),
                f"Status '{nome}' criado com cor {hex_color}",
                contexto=f"Nome: {nome}\nCor: {hex_color}")

            elif action == 'edit_status':
                active_tab = 'status'
                status_id = int(request.form.get('id')) if request.form.get('id') else None
                nome = proteger_input(request.form.get('nome'))
                hex_color = proteger_input(request.form.get('hex_color'))
                ativo = 1 if request.form.get('ativo') == '1' else 0
                update_status_processo(status_id, nome, hex_color, ativo)
                flash(f"Status '{nome}' atualizado!", 'success')
                gravar_log("Status editado", None, usuario_id, get_client_ip(),
                f"Status ID {status_id}: {nome}",
                contexto=f"ID: {status_id} | Nome: {nome}")

            elif action == 'toggle_status':
                active_tab = 'status'
                status_id = int(request.form.get('id')) if request.form.get('id') else None
                toggle_status_processo(status_id)
                flash("Status alterado!", 'success')

            elif action == 'add_service':
                active_tab = 'services'
                nome = proteger_input(request.form.get('nome'))
                descricao = proteger_input(request.form.get('descricao'))
                prazo_raw = request.form.get('prazo_padrao')
                prazo = int(prazo_raw) if prazo_raw and prazo_raw.isdigit() else 0
                add_tipo_servico(nome, descricao, prazo)
                flash(f"Serviço '{nome}' adicionado!", 'success')
                gravar_log("Tipo de serviço adicionado", None, usuario_id, get_client_ip(),
                f"Serviço '{nome}' adicionado",
                contexto=f"Nome: {nome}\nPrazo padrão: {prazo} dias")

            elif action == 'edit_service':
                active_tab = 'services'
                service_id = int(request.form.get('id')) if request.form.get('id') else None
                nome = proteger_input(request.form.get('nome'))
                descricao = proteger_input(request.form.get('descricao'))
                prazo_raw = request.form.get('prazo_padrao')
                prazo = int(prazo_raw) if prazo_raw and prazo_raw.isdigit() else 0
                ativo = 1 if request.form.get('ativo') == '1' else 0
                update_tipo_servico(service_id, nome, descricao, ativo, prazo)
                flash(f"Serviço '{nome}' atualizado!", 'success')
                gravar_log("Tipo de serviço editado", None, usuario_id, get_client_ip(),
                f"Serviço ID {service_id}: {nome}",
                contexto=f"ID: {service_id} | Nome: {nome}")

            elif action == 'toggle_service':
                active_tab = 'services'
                service_id = int(request.form.get('id')) if request.form.get('id') else None
                toggle_tipo_servico(service_id)
                flash("Tipo de serviço alterado!", 'success')

        except ValueError as e:
            logger.warning(f"Erro de validação nas configurações: {e}")
            if is_ajax:
                return jsonify({'success': False, 'message': str(e)})
            flash(f"Erro: {str(e)}", 'danger')
        except Exception as e:
            logger.exception(f"Erro ao processar configurações: {e}")
            if is_ajax:
                return jsonify({'success': False, 'message': f"Erro inesperado: {str(e)}"})
            flash(f"Erro inesperado: {str(e)}", 'danger')

        if request.form.get('return_to') == 'backup':
            return redirect(url_for('backup.index', config='1'))
        return redirect(url_for('configuracoes.index', tab=active_tab))

    # GET request
    try:
        email_config = get_email_config()
        backup_config = get_backup_config()
        tipos_processo = obter_tipos_servico()
        status_processo = obter_status_processo_config()
        
        if email_config:
            email_config['mail_server'] = email_config.get('smtp_host', '')
            email_config['mail_port'] = email_config.get('smtp_port', 587)
            email_config['mail_username'] = email_config.get('smtp_username', '')
            email_config['mail_password'] = email_config.get('smtp_password', '')
            email_config['mail_default_sender'] = email_config.get('sender_email', '')
            email_config['mail_use_tls'] = (email_config.get('smtp_encryption') == 'tls')
            email_config['mail_use_ssl'] = (email_config.get('smtp_encryption') == 'ssl')

        db_config = {
            'path_completo': Config.DATABASE_PATH
        }
        
        # Carrega dados da empresa para aba Estabelecimento
        from models import get_empresa_info
        from utils.file_uploads import get_image_url_for_display
        empresa_data = get_empresa_info() or {}
        display_logo_url = get_image_url_for_display(empresa_data.get('logo'), is_company_logo=True)

        from utils.helpers import get_contrast_color
        csrf_token_val = gerar_csrf_token()

        atividades_recentes = []
        atividades_total = 0
        if active_tab == 'atividades' and pode_ver_atividades:
            atividades_recentes = executar_query(
                """SELECT H.id, H.acao, H.contexto, H.processo_id, H.ip, H.timestamp, U.nome AS usuario_nome
                   FROM logs H LEFT JOIN usuarios U ON H.usuario_id = U.id
                   ORDER BY H.timestamp DESC, H.id DESC LIMIT 50"""
            )
            total_atividades_row = executar_query("SELECT COUNT(*) AS count FROM logs", fetch_one=True)
            atividades_total = total_atividades_row['count'] if total_atividades_row else 0

        return render_template('configuracoes.html',
                               email_config=email_config,
                               backup_config=backup_config,
                               tipos_processo=tipos_processo,
                               status_list=status_processo,
                               db_config=db_config,
                               active_tab=active_tab,
                               DEFAULT_BACKUP_PATH=Config.DEFAULT_BACKUP_PATH,
                               UPLOAD_PROCESSOS_DIR=Config.UPLOAD_PROCESSOS_DIR,
                               csrf_token=csrf_token_val,
                               get_contrast_color=get_contrast_color,
                               empresa=empresa_data,
                               display_logo_url=display_logo_url,
                               pode_ver_atividades=pode_ver_atividades,
                               atividades_recentes=atividades_recentes,
                               atividades_total=atividades_total)
    except Exception as e:
        logger.exception(f"Erro ao carregar página de configurações: {e}")
        flash(f"Erro ao carregar configurações: {str(e)}", 'danger')
        return redirect(url_for('auth.dashboard'))
