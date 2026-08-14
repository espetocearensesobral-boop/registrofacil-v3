# registrofacil/utils/scheduler.py
# Gerado por Gemini em 2025-07-14 14:25:00 -03 - Versão FINAL para o caminho do backup agendado

import os
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
from utils.logger import logger, manutencao_logger
from utils.logger_config import limpar_logs_antigos

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

    if scheduler.running:
        logger.info("Scheduler já está rodando. Removendo jobs existentes para reconfigurar.")
        scheduler.remove_all_jobs()
    else:
        logger.info("Scheduler não está rodando. Iniciando e configurando.")
        scheduler.start()
        _scheduler_initialized = True
    
    backup_config = None
    try:
        with app_context_callback():
            backup_config = get_backup_config()
    except Exception as e:
        logger.error(f"Erro ao carregar configurações de backup para o scheduler: {e}", exc_info=True)
        return

    if not backup_config or not backup_config.get('auto_backup_enabled'):
        logger.info("Backup automático desativado nas configurações. Nenhum job de backup agendado.")
        scheduler.remove_all_jobs()
        return

    logger.info("Configurando job de backup automático...")
    job_id = 'registrofacil_auto_backup_job'

    try:
        backup_frequency = backup_config['backup_frequency']
        backup_time_str = backup_config['backup_time']
        
        if not backup_time_str:
            logger.error("Hora de backup não configurada. Backup automático não será agendado.")
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
                args=[app_context_callback]
            )
            logger.info(f"Job de backup diário agendado para {backup_time_str} (Horário de Fortaleza).")
        
        elif backup_frequency == 'weekly':
            backup_days = backup_config.get('backup_days', '').split(',')
            if not backup_days:
                logger.error("Dias da semana não configurados para backup semanal. Job não agendado.")
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
                logger.error(f"Nenhum dia de semana válido configurado para backup semanal: {backup_days}. Job não agendado.")
                return

            scheduler.add_job(
                perform_scheduled_backup,
                'cron',
                day_of_week=','.join(days_of_week_apscheduler),
                hour=backup_hour,
                minute=backup_minute,
                id=job_id,
                replace_existing=True,
                args=[app_context_callback]
            )
            logger.info(f"Job de backup semanal agendado para {backup_time_str} nos dias {backup_days} (Horário de Fortaleza).")

        elif backup_frequency == 'monthly':
            backup_day_of_month = backup_config.get('backup_day_of_month')
            if backup_day_of_month is None or not (1 <= backup_day_of_month <= 31):
                logger.error(f"Dia do mês inválido para backup mensal: {backup_day_of_month}. Job não agendado.")
                return

            scheduler.add_job(
                perform_scheduled_backup,
                'cron',
                day=backup_day_of_month,
                hour=backup_hour,
                minute=backup_minute,
                id=job_id,
                replace_existing=True,
                args=[app_context_callback]
            )
            logger.info(f"Job de backup mensal agendado para o dia {backup_day_of_month} às {backup_time_str} (Horário de Fortaleza).")
        
        else:
            logger.error(f"Frequência de backup inválida ou não suportada: {backup_frequency}. Job não agendado.")
            scheduler.remove_all_jobs()
            return

        logger.info("Scheduler de backup automático configurado com sucesso!")

    except Exception as e:
        logger.critical(f"Falha CRÍTICA ao configurar o scheduler de backup automático: {e}", exc_info=True)
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
        logger.info(f"Iniciando backup do banco de dados para temporário do sistema: {db_temp_path}")
        
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
                logger.error(f"Falha ao remover arquivo temporário parcial do DB {db_temp_path}: {exc}")
        
        raise Exception(f"Falha no backup do banco de dados: {str(e)}")

def add_folder_to_zip(zipf: zipfile.ZipFile, source: str, arcname: str) -> int:
    """Adiciona um diretório ao arquivo ZIP, verificando existência e permissões."""
    logger.info(f"Verificando diretório para backup: {source}")
    if not os.path.exists(source):
        logger.error(f"DIRETÓRIO CRÍTICO NÃO ENCONTRADO PARA BACKUP: {source}. Permissões ou caminho incorreto.")
        return 0
    if not os.path.isdir(source):
        logger.error(f"CAMINHO NÃO É UM DIRETÓRIO PARA BACKUP: {source}.")
        return 0
    if not os.access(source, os.R_OK):
        logger.error(f"SEM PERMISSÃO DE LEITURA PARA DIRETÓRIO DE BACKUP: {source}. Verifique as permissões.")
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

def perform_scheduled_backup(app_context_callback):
    """
    Realiza o backup automático completo do sistema.
    Executado pelo APScheduler.
    """
    with app_context_callback():
        logger.info("Iniciando execução do backup automático agendado...")
        user_id = 1

        final_zip_path = None
        db_temp_path = None
        
        try:
            backup_config = get_backup_config()
            local_backup_root_path_from_config = backup_config.get('local_path', Config.BACKUP_ROOT_DIR) 

            # Unificando diretório e nomenclatura
            scheduled_backup_dir = local_backup_root_path_from_config
            os.makedirs(scheduled_backup_dir, exist_ok=True) 
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file_name = f"registrofacil_bkp_{timestamp}.zip"
            full_backup_path = os.path.join(scheduled_backup_dir, backup_file_name) 
            
            temp_zip_buffer = BytesIO()

            with zipfile.ZipFile(temp_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                db_temp_path = create_temp_db_backup(scheduled_backup_dir) 
                zipf.write(db_temp_path, f"database/{os.path.basename(DATABASE_PATH)}")
                logger.info(f"Backup do DB adicionado ao ZIP ({os.path.getsize(db_temp_path)} bytes)")

                # Inclusão de anexos e pastas do sistema
                add_folder_to_zip(zipf, get_upload_folder(), 'uploads/processos')
                add_folder_to_zip(zipf, Config.EMPRESA_UPLOAD_FOLDER, 'uploads/empresa')
                add_folder_to_zip(zipf, Config.PROFILE_UPLOAD_FOLDER, 'uploads/perfil')
                add_folder_to_zip(zipf, Config.LOG_DIR, 'logs')

            if temp_zip_buffer.tell() == 0:
                logger.error("Buffer ZIP está vazio. Backup não será salvo fisicamente.")
                raise ValueError("Conteúdo do backup vazio.")

            with open(full_backup_path, 'wb') as f:
                temp_zip_buffer.seek(0)
                f.write(temp_zip_buffer.read())
            
            logger.info(f"Backup automático '{backup_file_name}' salvo localmente em '{scheduled_backup_dir}'.")

            if backup_config.get('cloud_provider') == 'sftp':
                logger.info("Iniciando upload SFTP do backup automático...")
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
                                    logger.error(f"Erro ao verificar existência de diretório SFTP '{current_path}': {stat_err}")
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
                                        logger.error(f"Erro ao verificar existência de diretório SFTP '{current_path}': {stat_err}")
                                        raise

                                for d in reversed(dirs_to_create):
                                    sftp_client.mkdir(d)
                                    logger.info(f"Diretório SFTP criado: {d}")
                            
                            sftp_mkdir_p(sftp, sftp_remote_path) 

                            sftp.put(full_backup_path, os.path.join(sftp_remote_path, backup_file_name))
                            logger.info(f"Backup '{backup_file_name}' enviado para SFTP em '{sftp_remote_path}'.")
                            gravar_log("Backup Automático SFTP", None, user_id, "Scheduler", f"Upload SFTP concluído: {backup_file_name}")

                except Exception as sftp_e:
                    logger.error(f"Falha no upload SFTP do backup automático: {sftp_e}", exc_info=True)
                    gravar_log("Backup Automático SFTP", None, user_id, "Scheduler", f"Falha no upload SFTP: {sftp_e}")

            update_last_backup_time()
            gravar_log("Backup Automático", None, user_id, "Scheduler", f"Backup completo concluído: {backup_file_name}")
            logger.info("Backup automático agendado concluído com sucesso.")

        except Exception as e:
            logger.critical(f"Erro CRÍTICO durante execução do backup automático: {e}", exc_info=True)
            gravar_log("Backup Automático", None, user_id, "Scheduler", f"Falha CRÍTICA: {e}")
        finally:
            if db_temp_path and os.path.exists(db_temp_path):
                temp_file_to_delete = db_temp_path
                renamed_path = None
                try:
                    renamed_path = f"{temp_file_to_delete}.deleteme_{secrets.token_hex(4)}"
                    os.rename(temp_file_to_delete, renamed_path)
                    logger.debug(f"Arquivo temporário de DB renomeado para exclusão: {temp_file_to_delete} -> {renamed_path}")
                    temp_file_to_delete = renamed_path
                except OSError as e:
                    logger.warning(f"Falha ao renomear arquivo temporário de DB: {temp_file_to_delete} - {e}. Tentando deletar o original.")
                    renamed_path = None
                
                target_path_for_deletion = renamed_path if renamed_path else db_temp_path

                for i in range(15): 
                    try:
                        os.remove(target_path_for_deletion)
                        logger.info(f"Arquivo temporário de DB {target_path_for_deletion} removido com sucesso.")
                        break
                    except OSError as e:
                        if i < 14:
                            logger.warning(f"Falha ao limpar arquivo temporário de DB {target_path_for_deletion}: {e}. Tentando novamente em 1.0s...") 
                            time.sleep(1.0)
                        else:
                            logger.warning(f"Falha persistente ao limpar arquivo temporário de DB {target_path_for_deletion}: {e}")
                            gravar_log("Backup Automático", None, user_id, "Scheduler", f"Falha na limpeza de temp DB: {target_path_for_deletion}")
                    except Exception as e:
                        logger.warning(f"Erro inesperado ao limpar arquivo temporário de DB {target_path_for_deletion}: {e}")
                        gravar_log("Backup Automático", None, user_id, "Scheduler", f"Erro inesperado na limpeza de temp DB: {target_path_for_deletion}, Erro: {e}")
            else:
                logger.debug("Nenhum arquivo temporário de DB para limpar.")