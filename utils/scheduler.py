# registrofacil/utils/scheduler.py
# Gerado por Gemini em 2025-07-14 14:25:00 -03 - Versão FINAL para o caminho do backup agendado

import os
import posixpath
import zipfile
import shutil
import sqlite3
from datetime import datetime
import time
import tempfile
import secrets
import gc
import paramiko
from io import BytesIO # Adicionado: Importação de BytesIO

from models import DATABASE_PATH, gravar_log, get_backup_config, update_last_backup_time, get_upload_folder
from config import Config 
from utils.logger import manutencao_logger
from utils.logger_config import limpar_logs_antigos
from utils.backup_service import create_backup_archive, validate_backup_archive, write_backup_status, apply_retention

# === Configuração do Scheduler (APScheduler) ===
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone
import logging

logging.getLogger('apscheduler').setLevel(logging.WARNING)

scheduler = BackgroundScheduler(timezone=timezone('America/Fortaleza'))

_scheduler_initialized = False

def configure_and_start_scheduler(app_context_callback):
    global _scheduler_initialized

    if not scheduler.running:
        manutencao_logger.info("Scheduler não está rodando. Iniciando e configurando.")
        scheduler.start()
        _scheduler_initialized = True

    job_id = 'registrofacil_auto_backup_job'
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass

    if not Config.INTERNAL_BACKUP_SCHEDULER_ENABLED:
        manutencao_logger.info("Scheduler interno de backup desativado; use python -m utils.backup_runner.")
        return
    
    backup_config = None
    try:
        with app_context_callback():
            backup_config = get_backup_config()
    except Exception as e:
        manutencao_logger.error(f"Erro ao carregar configurações de backup para o scheduler: {e}", exc_info=True)
        return

    if not backup_config or not backup_config.get('auto_backup_enabled'):
        manutencao_logger.info("Backup automático desativado nas configurações. Nenhum job de backup agendado.")
        return

    manutencao_logger.info("Configurando job de backup automático...")

    try:
        backup_frequency = backup_config['backup_frequency']
        backup_time_str = backup_config['backup_time']
        
        if not backup_time_str:
            manutencao_logger.error("Hora de backup não configurada. Backup automático não será agendado.")
            return

        backup_hour, backup_minute = map(int, backup_time_str.split(':'))

        if backup_frequency == 'daily':
            scheduler.add_job(
                perform_scheduled_backup,
                'cron',
                hour=backup_hour,
                minute=backup_minute,
                id=job_id,
                replace_existing=True,
                args=[app_context_callback],
                max_instances=1,
                coalesce=True,
                misfire_grace_time=3600,
            )
            manutencao_logger.info(f"Job de backup diário agendado para {backup_time_str} (Horário de Fortaleza).")
        
        elif backup_frequency == 'weekly':
            backup_days = backup_config.get('backup_days', '').split(',')
            if not backup_days:
                manutencao_logger.error("Dias da semana não configurados para backup semanal. Job não agendado.")
                return
            
            days_of_week_apscheduler = []
            for d in backup_days:
                d_lower = d.strip().lower()
                if d_lower in ['domingo', 'sunday', 'sun']: days_of_week_apscheduler.append('sun')
                elif d_lower in ['segunda-feira', 'segunda', 'monday', 'mon']: days_of_week_apscheduler.append('mon')
                elif d_lower in ['terça-feira', 'terca', 'tuesday', 'tue']: days_of_week_apscheduler.append('tue')
                elif d_lower in ['quarta-feira', 'quarta', 'wednesday', 'wed']: days_of_week_apscheduler.append('wed')
                elif d_lower in ['quinta-feira', 'quinta', 'thursday', 'thu']: days_of_week_apscheduler.append('thu')
                elif d_lower in ['sexta-feira', 'sexta', 'friday', 'fri']: days_of_week_apscheduler.append('fri')
                elif d_lower in ['sábado', 'sabado', 'saturday', 'sat']: days_of_week_apscheduler.append('sat')

            if not days_of_week_apscheduler:
                manutencao_logger.error(f"Nenhum dia de semana válido configurado para backup semanal: {backup_days}. Job não agendado.")
                return

            scheduler.add_job(
                perform_scheduled_backup,
                'cron',
                day_of_week=','.join(days_of_week_apscheduler),
                hour=backup_hour,
                minute=backup_minute,
                id=job_id,
                replace_existing=True,
                args=[app_context_callback],
                max_instances=1,
                coalesce=True,
                misfire_grace_time=3600,
            )
            manutencao_logger.info(f"Job de backup semanal agendado para {backup_time_str} nos dias {backup_days} (Horário de Fortaleza).")

        elif backup_frequency == 'monthly':
            backup_day_of_month = backup_config.get('backup_day_of_month')
            if backup_day_of_month is None or not (1 <= backup_day_of_month <= 31):
                manutencao_logger.error(f"Dia do mês inválido para backup mensal: {backup_day_of_month}. Job não agendado.")
                return

            scheduler.add_job(
                perform_scheduled_backup,
                'cron',
                day=backup_day_of_month,
                hour=backup_hour,
                minute=backup_minute,
                id=job_id,
                replace_existing=True,
                args=[app_context_callback],
                max_instances=1,
                coalesce=True,
                misfire_grace_time=3600,
            )
            manutencao_logger.info(f"Job de backup mensal agendado para o dia {backup_day_of_month} às {backup_time_str} (Horário de Fortaleza).")
        
        else:
            manutencao_logger.error(f"Frequência de backup inválida ou não suportada: {backup_frequency}. Job não agendado.")
            scheduler.remove_all_jobs()
            return

        manutencao_logger.info("Scheduler de backup automático configurado com sucesso!")

    except Exception as e:
        manutencao_logger.critical(f"Falha CRÍTICA ao configurar o scheduler de backup automático: {e}", exc_info=True)
        scheduler.remove_all_jobs()

def create_temp_db_backup(target_dir: str) -> str:
    """Cria uma cópia temporária do banco de dados para backup em um diretório temporário do sistema."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    db_temp_file = f"registrofacil_temp_db_{timestamp}_{secrets.token_hex(4)}.db"
    
    temp_dir_for_db = Config.TEMP_DIR 
    db_temp_path = os.path.join(temp_dir_for_db, db_temp_file)
    
    conn = None
    dest_conn = None

    try:
        manutencao_logger.info(f"Iniciando backup do banco de dados para temporário do sistema: {db_temp_path}")
        
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
        if dest_conn:
            dest_conn.close()
        if conn:
            conn.close()
        
        if os.path.exists(db_temp_path):
            try:
                os.remove(db_temp_path)
            except OSError as exc:
                manutencao_logger.error(f"Falha ao remover arquivo temporário parcial do DB {db_temp_path}: {exc}")
        
        raise Exception(f"Falha no backup do banco de dados: {str(e)}")

def add_folder_to_zip(zipf: zipfile.ZipFile, source: str, arcname: str) -> int:
    """Adiciona um diretório ao arquivo ZIP, verificando existência e permissões."""
    manutencao_logger.info(f"Verificando diretório para backup: {source}")
    if not os.path.exists(source):
        manutencao_logger.error(f"DIRETÓRIO CRÍTICO NÃO ENCONTRADO PARA BACKUP: {source}. Permissões ou caminho incorreto.")
        return 0
    if not os.path.isdir(source):
        manutencao_logger.error(f"CAMINHO NÃO É UM DIRETÓRIO PARA BACKUP: {source}.")
        return 0
    if not os.access(source, os.R_OK):
        manutencao_logger.error(f"SEM PERMISSÃO DE LEITURA PARA DIRETÓRIO DE BACKUP: {source}. Verifique as permissões.")
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
                manutencao_logger.error(f"Erro ao adicionar arquivo '{file_path}' ao ZIP: {str(e)}")
    manutencao_logger.info(f"Conteúdo de {source} ({count} arquivos) adicionado ao backup.")
    return count

def perform_scheduled_backup(app_context_callback):
    """
    Realiza o backup automático completo do sistema.
    Executado pelo APScheduler.
    """
    with app_context_callback():
        manutencao_logger.info("Iniciando execução do backup automático agendado...")
        user_id = 1

        final_zip_path = None
        db_temp_path = None
        remote_status = "not_configured"
        remote_error = None
        
        try:
            backup_config = get_backup_config()
            scheduled_backup_dir = backup_config.get('local_path', Config.BACKUP_ROOT_DIR)
            result = create_backup_archive(
                destination_dir=scheduled_backup_dir,
                database_path=DATABASE_PATH,
                upload_processos=get_upload_folder(),
                upload_empresa=Config.EMPRESA_UPLOAD_FOLDER,
                log_dir=Config.LOG_DIR,
                source="scheduled",
            )
            backup_file_name = result['filename']
            full_backup_path = result['path']
            final_zip_path = full_backup_path
            validate_backup_archive(full_backup_path)
            apply_retention(scheduled_backup_dir)
            write_backup_status(scheduled_backup_dir, status="success_local", source="scheduled", result=result)
            manutencao_logger.info(
                f"Backup automático '{backup_file_name}' salvo e verificado em "
                f"'{scheduled_backup_dir}' (SHA-256: {result['sha256']})."
            )

            if backup_config.get('cloud_provider') == 'sftp':
                manutencao_logger.info("Iniciando upload SFTP do backup automático...")
                try:
                    sftp_host = backup_config['sftp_host']
                    sftp_port = backup_config.get('sftp_port', 22)
                    sftp_username = backup_config['sftp_username']
                    sftp_password = backup_config['sftp_password']
                    sftp_remote_path = backup_config['sftp_remote_path']
                    
                    if not all([sftp_host, sftp_username, sftp_password, sftp_remote_path]):
                        raise ValueError("Configurações SFTP incompletas.")

                    with paramiko.Transport((sftp_host, sftp_port)) as transport:
                        transport.connect(username=sftp_username, password=sftp_password)
                        with paramiko.SFTPClient.from_transport(transport) as sftp:
                            def sftp_mkdir_p(sftp_client, remote_directory):
                                dirs_to_create = []
                                current_path = remote_directory
                                try:
                                    sftp_client.lstat(current_path)
                                    return
                                except FileNotFoundError:
                                    pass
                                except Exception as stat_err:
                                    manutencao_logger.error(f"Erro ao verificar existência de diretório SFTP '{current_path}': {stat_err}")
                                    raise

                                while current_path and current_path != '/' and current_path != '.':
                                    try:
                                        sftp_client.lstat(current_path)
                                        break
                                    except FileNotFoundError:
                                        dirs_to_create.append(current_path)
                                        current_path = os.path.dirname(current_path.rstrip('/'))
                                        if not current_path: 
                                            current_path = '/'
                                    except Exception as stat_err:
                                        manutencao_logger.error(f"Erro ao verificar existência de diretório SFTP '{current_path}': {stat_err}")
                                        raise

                                for d in reversed(dirs_to_create):
                                    sftp_client.mkdir(d)
                                    manutencao_logger.info(f"Diretório SFTP criado: {d}")
                            
                            sftp_mkdir_p(sftp, sftp_remote_path) 

                            remote_target = posixpath.join(sftp_remote_path, backup_file_name)
                            sftp.put(full_backup_path, remote_target)
                            remote_stat = sftp.stat(remote_target)
                            if int(remote_stat.st_size) != int(result['size']):
                                raise IOError("O tamanho remoto diverge do backup local.")
                            remote_status = "success_remote"
                            write_backup_status(scheduled_backup_dir, status=remote_status, source="scheduled", result=result)
                            manutencao_logger.info(f"Backup '{backup_file_name}' enviado e verificado no SFTP em '{remote_target}'.")
                            gravar_log("Backup Automático SFTP", None, user_id, "Scheduler", f"Upload SFTP concluído: {backup_file_name}")

                except Exception as sftp_e:
                    remote_status = "partial"
                    remote_error = str(sftp_e)
                    write_backup_status(scheduled_backup_dir, status=remote_status, source="scheduled", result=result, error=remote_error)
                    manutencao_logger.error(f"Falha no upload SFTP do backup automático: {sftp_e}", exc_info=True)
                    gravar_log("Backup Automático SFTP", None, user_id, "Scheduler", f"Falha no upload SFTP: {sftp_e}")

            update_last_backup_time()
            gravar_log(
                "Backup Automático", None, user_id, "Scheduler",
                f"Backup local concluído: {backup_file_name} | status={remote_status} | "
                f"SHA-256: {result['sha256']}" + (f" | erro remoto: {remote_error}" if remote_error else "")
            )
            manutencao_logger.info("Backup automático agendado concluído com sucesso.")

        except Exception as e:
            manutencao_logger.critical(f"Erro CRÍTICO durante execução do backup automático: {e}", exc_info=True)
            try:
                write_backup_status(locals().get('scheduled_backup_dir', Config.BACKUP_ROOT_DIR), status="failed", source="scheduled", error=str(e))
            except Exception:
                manutencao_logger.warning("Falha ao persistir status de erro do backup agendado.", exc_info=True)
            gravar_log("Backup Automático", None, user_id, "Scheduler", f"Falha CRÍTICA: {e}")
        finally:
            if db_temp_path and os.path.exists(db_temp_path):
                temp_file_to_delete = db_temp_path
                renamed_path = None
                try:
                    renamed_path = f"{temp_file_to_delete}.deleteme_{secrets.token_hex(4)}"
                    os.rename(temp_file_to_delete, renamed_path)
                    manutencao_logger.debug(f"Arquivo temporário de DB renomeado para exclusão: {temp_file_to_delete} -> {renamed_path}")
                    temp_file_to_delete = renamed_path
                except OSError as e:
                    manutencao_logger.warning(f"Falha ao renomear arquivo temporário de DB: {temp_file_to_delete} - {e}. Tentando deletar o original.")
                    renamed_path = None
                
                target_path_for_deletion = renamed_path if renamed_path else db_temp_path

                for i in range(15): 
                    try:
                        os.remove(target_path_for_deletion)
                        manutencao_logger.info(f"Arquivo temporário de DB {target_path_for_deletion} removido com sucesso.")
                        break
                    except OSError as e:
                        if i < 14:
                            manutencao_logger.warning(f"Falha ao limpar arquivo temporário de DB {target_path_for_deletion}: {e}. Tentando novamente em 1.0s...")
                            time.sleep(1.0)
                        else:
                            manutencao_logger.warning(f"Falha persistente ao limpar arquivo temporário de DB {target_path_for_deletion}: {e}")
                            gravar_log("Backup Automático", None, user_id, "Scheduler", f"Falha na limpeza de temp DB: {target_path_for_deletion}")
                    except Exception as e:
                        manutencao_logger.warning(f"Erro inesperado ao limpar arquivo temporário de DB {target_path_for_deletion}: {e}")
                        gravar_log("Backup Automático", None, user_id, "Scheduler", f"Erro inesperado na limpeza de temp DB: {target_path_for_deletion}, Erro: {e}")
            else:
                manutencao_logger.debug("Nenhum arquivo temporário de DB para limpar.")