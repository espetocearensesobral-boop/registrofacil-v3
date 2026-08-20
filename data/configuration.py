"""Serviços de configuração, e-mail e backup.

As funções mantêm as assinaturas legadas para compatibilidade com as rotas
e com o scheduler.
"""

from config import Config
from data.crypto import encrypt, decrypt
from data.database import executar_query
from utils.logger import sistema_logger as logger

def get_config(key):
    result = executar_query("SELECT valor FROM configuracoes WHERE chave = ?", [key], fetch_one=True)
    return result['valor'] if result else None

def set_config(key, value):
    try:
        rows_affected = executar_query("UPDATE configuracoes SET valor = ?, updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE chave = ?", [value, key])
        if rows_affected == 0:
            executar_query("INSERT INTO configuracoes (chave, valor, updated_at) VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))", [key, value])
        logger.info(f"Configuração '{key}' definida/atualizada para '{value}'.")
        return True
    except Exception as e:
        logger.error(f"Erro ao definir/atualizar configuração '{key}': {e}", exc_info=True)
        return False

def obter_status_processo_config():
    return executar_query("""
        SELECT sp.id, sp.nome, sp.hex_color, sp.ativo, 
        (SELECT COUNT(*) FROM processos p WHERE p.status_id = sp.id) as total_processos
        FROM status_processo sp 
        ORDER BY sp.nome ASC
    """)

def get_email_config():
    config = {
        'id': None,
        'smtp_host': '',
        'smtp_port': 587,
        'smtp_encryption': 'tls',
        'smtp_username': '',
        'smtp_password': '',
        'sender_email': '',
        'sender_name': 'Registro Fácil',
        'ativo': 0,
        'notify_password_recovery': 1,
        'notify_deadlines': 1,
        'notify_backup_failures': 1,
        'notify_security_events': 1,
    }

    result = executar_query("SELECT * FROM email_config LIMIT 1", fetch_one=True)
    if result:
        config.update({key: result[key] for key in result.keys()})
        if config['smtp_password']:
            decrypted_pass = decrypt(config['smtp_password'])
            config['smtp_password'] = decrypted_pass if decrypted_pass is not None else ''
        else:
            config['smtp_password'] = ''

    encryption = config.get('smtp_encryption') or 'tls'
    if encryption not in {'none', 'tls', 'ssl'}:
        encryption = 'tls'
    config['smtp_encryption'] = encryption

    # Aliases de compatibilidade com o formulário administrativo legado.
    config.update({
        'mail_server': config.get('smtp_host', ''),
        'mail_port': config.get('smtp_port', 587),
        'mail_username': config.get('smtp_username', ''),
        'mail_default_sender': config.get('sender_email', ''),
        'mail_use_tls': encryption == 'tls',
        'mail_use_ssl': encryption == 'ssl',
    })
    return config


def email_notification_enabled(notification_key: str) -> bool:
    """Retorna se o SMTP e uma política específica de notificação estão ativos."""
    config = get_email_config()
    return bool(config.get('ativo')) and bool(config.get(notification_key, 1))


def save_email_config(config_data, is_new_config=False, connection=None):
    smtp_password_raw = config_data.get('smtp_password')
    encrypted_password = None

    # Resolve se é INSERT ou UPDATE: prioriza o ID informado,
    # mas também verifica se já existe um registro com o mesmo smtp_username
    # (evita UNIQUE constraint ao salvar após um teste bem-sucedido sem ID).
    config_id = config_data.get('id')
    if not config_id or config_id <= 0:
        existing = executar_query(
            "SELECT id FROM email_config WHERE smtp_username = ? LIMIT 1",
            [config_data['smtp_username']], fetch_one=True, connection=connection
        )
        if existing:
            config_id = existing['id']
        else:
            any_existing = executar_query(
                "SELECT id FROM email_config LIMIT 1",
                fetch_one=True, connection=connection
            )
            if any_existing:
                config_id = any_existing['id']

    is_update = bool(config_id and config_id > 0)

    if smtp_password_raw:
        encrypted_password = encrypt(smtp_password_raw)
        if encrypted_password is None:
            logger.error("Falha ao criptografar a senha. Retornando erro.")
            raise ValueError("Falha ao criptografar a senha. Verifique a chave de criptografia.")
    elif is_update:
        current_config_db = executar_query(
            "SELECT smtp_password FROM email_config WHERE id = ? LIMIT 1",
            [config_id], fetch_one=True, connection=connection
        )
        if current_config_db:
            encrypted_password = current_config_db['smtp_password']

    if config_data.get('ativo'):
        executar_query(
            "UPDATE email_config SET ativo = 0 WHERE ativo = 1 AND id != ?",
            [config_id or 0], connection=connection
        )

    if not is_update:
        if not smtp_password_raw:
            raise ValueError("A senha SMTP é obrigatória para uma nova configuração.")
        res = executar_query(
            """INSERT INTO email_config (smtp_host, smtp_port, smtp_encryption, smtp_username, smtp_password, sender_email, sender_name, ativo,
               notify_password_recovery, notify_deadlines, notify_backup_failures, notify_security_events, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))""",
            [config_data['smtp_host'], config_data['smtp_port'], config_data['smtp_encryption'],
             config_data['smtp_username'], encrypted_password, config_data['sender_email'],
             config_data['sender_name'], config_data['ativo'],
             config_data.get('notify_password_recovery', 1), config_data.get('notify_deadlines', 1),
             config_data.get('notify_backup_failures', 1), config_data.get('notify_security_events', 1)],
            connection=connection
        )
        return bool(res)
    else:
        res = executar_query(
            """UPDATE email_config SET smtp_host = ?, smtp_port = ?, smtp_encryption = ?,
               smtp_username = ?, smtp_password = ?, sender_email = ?, sender_name = ?, ativo = ?,
               notify_password_recovery = ?, notify_deadlines = ?, notify_backup_failures = ?, notify_security_events = ?,
               updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
               WHERE id = ?""",
            [config_data['smtp_host'], config_data['smtp_port'], config_data['smtp_encryption'],
             config_data['smtp_username'], encrypted_password, config_data['sender_email'],
             config_data['sender_name'], config_data['ativo'],
             config_data.get('notify_password_recovery', 1), config_data.get('notify_deadlines', 1),
             config_data.get('notify_backup_failures', 1), config_data.get('notify_security_events', 1), config_id],
            connection=connection
        )
        return bool(res)

def send_email(to_address, subject, body, sender_name=None, sender_email=None, app_instance=None, email_config_override=None):
    from flask_mail import Message, Mail # Mantenha a importação aqui

    if app_instance is None:
        logger.error("send_email chamado sem a instância 'app_instance'. Não é possível enviar o e-mail.")
        return False, "Erro interno: Instância do aplicativo Flask não fornecida para envio de e-mail."

    email_config = email_config_override or get_email_config()
    if not email_config or not email_config.get('ativo'):
        logger.warning("Tentativa de enviar e-mail, mas a configuração de e-mail não está ativa ou não foi encontrada.")
        return False, "Configuração de e-mail não ativa ou não encontrada."

    _sender_name = sender_name if sender_name else email_config['sender_name']
    _sender_email = sender_email if sender_email else email_config['sender_email']

    # Salva as configurações originais antes de modificá-las
    original_mail_configs = {
        'MAIL_SERVER': app_instance.config.get('MAIL_SERVER'),
        'MAIL_PORT': app_instance.config.get('MAIL_PORT'),
        'MAIL_USE_TLS': app_instance.config.get('MAIL_USE_TLS'),
        'MAIL_USE_SSL': app_instance.config.get('MAIL_USE_SSL'),
        'MAIL_USERNAME': app_instance.config.get('MAIL_USERNAME'),
        'MAIL_PASSWORD': app_instance.config.get('MAIL_PASSWORD'),
        'MAIL_DEFAULT_SENDER': app_instance.config.get('MAIL_DEFAULT_SENDER')
    }

    # <----- PONTO CRÍTICO DA CORREÇÃO: Atualize app.config PRIMEIRO ----->
    app_instance.config['MAIL_SERVER'] = email_config['smtp_host']
    app_instance.config['MAIL_PORT'] = email_config['smtp_port']
    app_instance.config['MAIL_USE_TLS'] = (email_config['smtp_encryption'] == 'tls')
    app_instance.config['MAIL_USE_SSL'] = (email_config['smtp_encryption'] == 'ssl')
    app_instance.config['MAIL_USERNAME'] = email_config['smtp_username']
    app_instance.config['MAIL_PASSWORD'] = email_config['smtp_password'] # Já descriptografado por get_email_config
    app_instance.config['MAIL_DEFAULT_SENDER'] = (_sender_name, _sender_email)

    logger.debug(f"DEBUG E-MAIL: Configurações de envio a serem usadas:")
    logger.debug(f"  MAIL_SERVER: {app_instance.config.get('MAIL_SERVER')}")
    logger.debug(f"  MAIL_PORT: {app_instance.config.get('MAIL_PORT')}")
    logger.debug(f"  MAIL_USE_TLS: {app_instance.config.get('MAIL_USE_TLS')}")
    logger.debug(f"  MAIL_USE_SSL: {app_instance.config.get('MAIL_USE_SSL')}")
    logger.debug(f"  MAIL_USERNAME: {app_instance.config.get('MAIL_USERNAME')}")
    logger.debug(f"  MAIL_PASSWORD: {'(senha presente)' if app_instance.config.get('MAIL_PASSWORD') else '(senha ausente)'}")
    logger.debug(f"  MAIL_DEFAULT_SENDER: {app_instance.config.get('MAIL_DEFAULT_SENDER')}")
    logger.debug(f"  Destinatário: {to_address}, Assunto: {subject}")

    # <----- PONTO CRÍTICO DA CORREÇÃO: Crie o objeto Mail SOMENTE AGORA ----->
    mail_instance = Mail(app_instance) 

    msg = Message(subject, sender=(_sender_name, _sender_email), recipients=[to_address])
    msg.body = body

    try:
        with app_instance.app_context():
            mail_instance.send(msg)
        logger.info(f"E-mail enviado com sucesso para {to_address} (Assunto: {subject}).")
        return True, "E-mail enviado com sucesso."
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail para {to_address} (Assunto: {subject}): {e}", exc_info=True)
        return False, f"Falha ao enviar e-mail: {e}"
    finally:
        # Restaura as configurações originais
        for key, value in original_mail_configs.items():
            if value is not None:
                app_instance.config[key] = value
            elif key in app_instance.config: # Se a chave não existia originalmente, remova-a
                del app_instance.config[key]

def get_backup_config():
    default_config = {
        'id': None,
        'local_path': Config.BACKUP_ROOT_DIR, 
        'cloud_provider': 'none',
        'sftp_host': '',
        'sftp_port': 22,
        'sftp_username': '',
        'sftp_password': '',
        'sftp_remote_path': '/backups/',
        'auto_backup_enabled': 0,
        'backup_frequency': 'daily',
        'backup_time': '02:00',
        'backup_days': [],
        'backup_day_of_month': 1,
        'last_backup_at': None
    }
    
    result = executar_query("SELECT * FROM backup_configs LIMIT 1", fetch_one=True)
    if result:
        config = dict(result)
        if config.get('sftp_password'):
            decrypted_pass = decrypt(config['sftp_password'])
            config['sftp_password'] = decrypted_pass if decrypted_pass is not None else ''
        else:
            config['sftp_password'] = ''
        
        if config.get('backup_days'):
            config['backup_days'] = config['backup_days'].split(',')
        else:
            config['backup_days'] = []
        
        default_config.update(config)
    return default_config

def save_backup_config(config_data, connection=None):
    sftp_password_raw = config_data.get('sftp_password')
    encrypted_sftp_password = None

    if sftp_password_raw:
        encrypted_sftp_password = encrypt(sftp_password_raw)
        if encrypted_sftp_password is None:
            logger.error("Falha ao criptografar a nova senha SFTP. Retornando erro.")
            raise ValueError("Falha ao criptografar a senha SFTP. Verifique a chave de criptografia.")
    elif config_data.get('id'):
        current_sftp_pass_result = executar_query("SELECT sftp_password FROM backup_configs WHERE id = ? LIMIT 1", [config_data['id']], fetch_one=True, connection=connection)
        if current_sftp_pass_result:
            encrypted_sftp_password = current_sftp_pass_result['sftp_password']
        logger.debug(f"Senha SFTP não fornecida, usando a senha existente (se houver) para config ID: {config_data.get('id')}")

    backup_days_db_format = ''
    if isinstance(config_data.get('backup_days'), list):
        backup_days_db_format = ','.join(config_data['backup_days'])
    elif config_data.get('backup_days') is not None:
        backup_days_db_format = str(config_data['backup_days'])

    auto_backup_enabled_db = 1 if config_data.get('auto_backup_enabled') in [1, '1', 'on', True] else 0
        
    params = [
        config_data.get('local_path'),
        config_data.get('cloud_provider'),
        config_data.get('sftp_host'),
        config_data.get('sftp_port'),
        config_data.get('sftp_username'),
        encrypted_sftp_password,
        config_data.get('sftp_remote_path'),
        auto_backup_enabled_db,
        config_data.get('backup_frequency'),
        config_data.get('backup_time'),
        backup_days_db_format,
        config_data.get('backup_day_of_month'),
        config_data.get('uploads_path')
    ]
    
    if config_data.get('id'):
        query = """
            UPDATE backup_configs SET
            local_path = ?, cloud_provider = ?, sftp_host = ?, sftp_port = ?,
            sftp_username = ?, sftp_password = ?, sftp_remote_path = ?,
            auto_backup_enabled = ?, backup_frequency = ?, backup_time = ?,
            backup_days = ?, backup_day_of_month = ?, uploads_path = ?,
            updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
            WHERE id = ?
        """
        params.append(config_data['id'])
        logger.debug(f"Atualizando backup_configs. ID: {config_data['id']}, Auto enabled: {auto_backup_enabled_db}")
        return executar_query(query, params, connection=connection)
    else:
        query = """
            INSERT INTO backup_configs (
                local_path, cloud_provider, sftp_host, sftp_port, sftp_username, sftp_password, sftp_remote_path,
                auto_backup_enabled, backup_frequency, backup_time, backup_days, backup_day_of_month, uploads_path,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """
        logger.debug(f"Inserindo nova backup_config. Auto enabled: {auto_backup_enabled_db}")
        return executar_query(query, params, connection=connection)

def update_last_backup_time(connection=None):
    config = get_backup_config()
    
    query = "UPDATE backup_configs SET last_backup_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = (SELECT id FROM backup_configs LIMIT 1)"
    logger.info("Atualizando last_backup_at no DB.")
    return executar_query(query, connection=connection)

