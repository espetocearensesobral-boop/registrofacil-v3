# registrofacil/config.py

import os
import sys
import secrets  # <<< CORREÇÃO ADICIONADA AQUI
from datetime import timedelta, datetime

# --- Lógica de Caminhos para .EXE e Desenvolvimento ---
if getattr(sys, 'frozen', False):
    # Se estiver rodando como .exe ('congelado' pelo PyInstaller)
    # BASE_DIR = pasta do .exe (C:\Program Files\...) → SOMENTE LEITURA
    # DATA_DIR = pasta de dados gravável pelo usuário (C:\ProgramData\RegistroFacil)
    # IMPORTANTE: C:\Program Files não permite gravação sem admin, por isso todos
    # os arquivos mutáveis (DB, logs, backups, uploads) devem usar DATA_DIR.
    BASE_DIR = os.path.dirname(sys.executable)
    DATA_DIR = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'RegistroFacil')
else:
    # Se estiver rodando como script .py normal
    # O caminho base é o diretório do arquivo config.py.
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BASE_DIR


class Config:
    VERSION = '3.22.2'
    ENVIRONMENT = os.environ.get('REGISTROFACIL_ENV', 'development').strip().lower()
    IS_PRODUCTION = ENVIRONMENT in {'production', 'prod'}
    INITIAL_ADMIN_PASSWORD = os.environ.get('INITIAL_ADMIN_PASSWORD')
    TRUST_PROXY_HEADERS = os.environ.get('TRUST_PROXY_HEADERS', 'false').strip().lower() == 'true'
    # Defina false quando o Agendador de Tarefas/cron externo assumir os backups.
    INTERNAL_BACKUP_SCHEDULER_ENABLED = os.environ.get(
        'REGISTROFACIL_INTERNAL_BACKUP_SCHEDULER', 'true'
    ).strip().lower() == 'true'
    # SECRET_KEY persistente: gerado uma vez e salvo em arquivo oculto.
    # Sem persistência, toda reinicialização invalida as sessões ativas dos usuários.
    _secret_key_file = os.path.join(DATA_DIR, '.secret_key')
    try:
        if os.environ.get('SECRET_KEY'):
            SECRET_KEY = os.environ.get('SECRET_KEY')
        elif os.path.exists(_secret_key_file):
            with open(_secret_key_file, 'r') as _f:
                SECRET_KEY = _f.read().strip()
        else:
            SECRET_KEY = secrets.token_hex(32)
            with open(_secret_key_file, 'w') as _f:
                _f.write(SECRET_KEY)
            # Ocultar no Windows
            if sys.platform == 'win32':
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(_secret_key_file, 0x2)
                except Exception:
                    pass
    except Exception:
        SECRET_KEY = secrets.token_hex(32)

    # O caminho do banco de dados usa DATA_DIR (gravável, sem exigir admin)
    DATABASE_PATH = os.path.join(DATA_DIR, 'registrofacil.db')

    # Define o tempo de vida da sessão por inatividade
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Segurança dos cookies de sessão
    SESSION_COOKIE_HTTPONLY = True   # Impede acesso JS ao cookie
    SESSION_COOKIE_SAMESITE = 'Lax'  # Proteção CSRF
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true' if IS_PRODUCTION else 'false').strip().lower() == 'true'

    TENTATIVAS_MAX = 5
    BLOQUEIO_TEMPO = 900

    # ENCRYPTION_KEY persistente: gerado na primeira execução e salvo em arquivo oculto.
    # NÃO usar valor hardcoded em produção - cada instalação deve ter sua própria chave.
    _enc_key_file = os.path.join(DATA_DIR, '.encryption_key')
    try:
        if os.environ.get('ENCRYPTION_KEY'):
            ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
        elif os.path.exists(_enc_key_file):
            with open(_enc_key_file, 'r') as _fk:
                ENCRYPTION_KEY = _fk.read().strip()
        else:
            from cryptography.fernet import Fernet
            ENCRYPTION_KEY = Fernet.generate_key().decode()
            with open(_enc_key_file, 'w') as _fk:
                _fk.write(ENCRYPTION_KEY)
            if sys.platform == 'win32':
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(_enc_key_file, 0x2)
                except Exception:
                    pass
    except Exception:
        # Fallback de emergência - não persiste, mas não bloqueia a inicialização
        from cryptography.fernet import Fernet
        ENCRYPTION_KEY = Fernet.generate_key().decode()

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    # Formatos permitidos para anexos de processos.
    # A validação final também confere o conteúdo real via libmagic.
    ALLOWED_EXTENSIONS = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
    }

    # Configurações de E-mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.example.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None and os.environ.get('MAIL_USE_TLS').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') is not None and os.environ.get('MAIL_USE_SSL').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or ''
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or '' 
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'no-reply@registrofacil.com'
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND') is not None and os.environ.get('MAIL_SUPPRESS_SEND').lower() == 'true'

    # --- Estrutura de Pastas de Log por Domínio ---
    # Logs ficam em DATA_DIR (C:\ProgramData\RegistroFacil\logs quando frozen)
    LOG_DIR = os.path.join(DATA_DIR, 'logs')
    # Domínios segregados (novos)
    AUTH_LOG_DIR        = os.path.join(LOG_DIR, 'auth')
    OPERACIONAL_LOG_DIR = os.path.join(LOG_DIR, 'operacional')
    SISTEMA_LOG_DIR     = os.path.join(LOG_DIR, 'sistema')
    MANUTENCAO_LOG_DIR  = os.path.join(LOG_DIR, 'manutencao')
    # Aliases de compatibilidade com versões anteriores
    APP_LOG_DIR      = OPERACIONAL_LOG_DIR
    ERROR_LOG_DIR    = OPERACIONAL_LOG_DIR
    SECURITY_LOG_DIR = AUTH_LOG_DIR
    # --- Fim da Estrutura de Log ---

    DEFAULT_LOGO_URL = '/static/img/logo_cartorio.png'

    # Estrutura de Backup - usa DATA_DIR (gravável sem admin)
    ROOT_BACKUP_FOLDER_NAME = 'backups'
    BACKUP_ROOT_DIR = os.path.join(DATA_DIR, ROOT_BACKUP_FOLDER_NAME)
    DEFAULT_BACKUP_PATH = BACKUP_ROOT_DIR

    # Uploads ficam em DATA_DIR quando frozen (C:\Program Files é somente leitura)
    UPLOAD_ROOT_FOLDER_NAME = 'uploads'
    PROCESSOS_UPLOAD_SUBFOLDER = 'processos'
    PERFIL_UPLOAD_SUBFOLDER = 'perfil'
    EMPRESA_UPLOAD_SUBFOLDER = 'empresa'
    # Modo .py (dev): uploads dentro de static/ para Flask servir via url_for('static').
    # Modo .exe (frozen): static/ é read-only no bundle PyInstaller, usa DATA_DIR.
    if getattr(sys, 'frozen', False):
        UPLOAD_ROOT_DIR = os.path.join(DATA_DIR, UPLOAD_ROOT_FOLDER_NAME)
    else:
        UPLOAD_ROOT_DIR = os.path.join(BASE_DIR, 'static', UPLOAD_ROOT_FOLDER_NAME)
    UPLOAD_PROCESSOS_DIR = os.path.join(UPLOAD_ROOT_DIR, PROCESSOS_UPLOAD_SUBFOLDER)
    PROFILE_UPLOAD_FOLDER = os.path.join(UPLOAD_ROOT_DIR, PERFIL_UPLOAD_SUBFOLDER)
    EMPRESA_UPLOAD_FOLDER = os.path.join(UPLOAD_ROOT_DIR, EMPRESA_UPLOAD_SUBFOLDER)

    TEMP_FOLDER_NAME = 'temp'
    TEMP_DIR = os.path.join(DATA_DIR, TEMP_FOLDER_NAME)

    try:
        # Garante que o DATA_DIR exista primeiro (quando frozen = C:\ProgramData\RegistroFacil)
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(AUTH_LOG_DIR, exist_ok=True)
        os.makedirs(OPERACIONAL_LOG_DIR, exist_ok=True)
        os.makedirs(SISTEMA_LOG_DIR, exist_ok=True)
        os.makedirs(MANUTENCAO_LOG_DIR, exist_ok=True)
        
        os.makedirs(UPLOAD_PROCESSOS_DIR, exist_ok=True)
        os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(EMPRESA_UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # CORRIGIDO: Cria apenas a pasta backups, sem subpastas
        os.makedirs(BACKUP_ROOT_DIR, exist_ok=True)
        
        # Teste de permissão de escrita
        with open(os.path.join(LOG_DIR, 'permission_test.log'), 'a') as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Teste de permissão de escrita ok.\n")

    except OSError as e:
        print(f"ERRO CRÍTICO: Não foi possível criar ou escrever nos diretórios. Verifique as permissões. Erro: {e}")
        sys.exit(1)