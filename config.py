# registrofacil/config.py

import os
import sys
import secrets
import stat
import hashlib
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


def _read_persistent_secret(path):
    """Lê um segredo persistente e restringe suas permissões locais."""
    with open(path, 'r', encoding='utf-8') as handle:
        value = handle.read().strip()
    if os.name != 'nt':
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return value


def _write_persistent_secret(path, value):
    """Cria um segredo com modo restritivo e evita sobrescrever um arquivo novo."""
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(value)
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    if os.name != 'nt':
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def _same_file_content(left_path, right_path):
    """Compara dois arquivos sem carregar seu conteúdo inteiro na memória."""
    if os.path.getsize(left_path) != os.path.getsize(right_path):
        return False
    left_hash = hashlib.sha256()
    right_hash = hashlib.sha256()
    with open(left_path, 'rb') as left_file, open(right_path, 'rb') as right_file:
        while True:
            left_chunk = left_file.read(1024 * 1024)
            right_chunk = right_file.read(1024 * 1024)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return left_hash.digest() == right_hash.digest()
            left_hash.update(left_chunk)
            right_hash.update(right_chunk)


def _migrate_legacy_public_uploads(legacy_root, private_root):
    """Move uploads antigos para fora de ``static`` sem alterar seus nomes.

    Versões anteriores guardavam anexos em ``static/uploads``. Como o Flask
    serve toda a árvore ``static`` publicamente, mantê-los ali contorna a rota
    autenticada de downloads. A migração é idempotente e preserva os nomes que
    já estão registrados no banco de dados.
    """
    for subfolder in ('processos', 'empresa'):
        source_dir = os.path.join(legacy_root, subfolder)
        destination_dir = os.path.join(private_root, subfolder)
        if not os.path.isdir(source_dir):
            continue
        os.makedirs(destination_dir, exist_ok=True)
        for root, _, filenames in os.walk(source_dir):
            relative_dir = os.path.relpath(root, source_dir)
            target_dir = destination_dir if relative_dir == '.' else os.path.join(destination_dir, relative_dir)
            os.makedirs(target_dir, exist_ok=True)
            for filename in filenames:
                source_path = os.path.join(root, filename)
                destination_path = os.path.join(target_dir, filename)
                if os.path.exists(destination_path):
                    if _same_file_content(source_path, destination_path):
                        os.remove(source_path)
                        continue
                    raise RuntimeError(
                        'Não foi possível migrar um upload legado porque já existe '
                        f'um arquivo diferente no destino: {destination_path}'
                    )
                os.replace(source_path, destination_path)


class Config:
    VERSION = '3.28.59'
    _configured_environment = os.environ.get('REGISTROFACIL_ENV', '').strip().lower()
    ENVIRONMENT = _configured_environment or 'production'
    IS_PRODUCTION = ENVIRONMENT in {'production', 'prod'}
    INITIAL_ADMIN_PASSWORD = os.environ.get('INITIAL_ADMIN_PASSWORD')
    TRUST_PROXY_HEADERS = os.environ.get('TRUST_PROXY_HEADERS', 'false').strip().lower() == 'true'
    # URL usada em links enviados por e-mail. Em rede local, configure como
    # http://IP-DO-SERVIDOR:5000; em produção, prefira HTTPS.
    PUBLIC_BASE_URL = os.environ.get('REGISTROFACIL_PUBLIC_URL', '').strip().rstrip('/')
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
            SECRET_KEY = _read_persistent_secret(_secret_key_file)
        else:
            SECRET_KEY = secrets.token_hex(32)
            _write_persistent_secret(_secret_key_file, SECRET_KEY)
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

    # Retenção persistente: operação pode ser expurgada; auditoria de segurança
    # permanece preservada por padrão até o administrador habilitar expurgo.
    LOG_DB_RETENTION_DAYS = int(os.environ.get('REGISTROFACIL_LOG_DB_RETENTION_DAYS', '365'))
    SECURITY_LOG_RETENTION_DAYS = int(os.environ.get('REGISTROFACIL_SECURITY_LOG_RETENTION_DAYS', '730'))
    PURGE_SECURITY_LOGS = os.environ.get('REGISTROFACIL_PURGE_SECURITY_LOGS', 'false').strip().lower() == 'true'

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
            ENCRYPTION_KEY = _read_persistent_secret(_enc_key_file)
        else:
            from cryptography.fernet import Fernet
            ENCRYPTION_KEY = Fernet.generate_key().decode()
            _write_persistent_secret(_enc_key_file, ENCRYPTION_KEY)
            if sys.platform == 'win32':
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(_enc_key_file, 0x2)
                except Exception:
                    pass
    except Exception as _encryption_error:
        if IS_PRODUCTION:
            raise RuntimeError(
                'Não foi possível carregar ou persistir a chave de criptografia. '
                'Corrija as permissões do diretório de dados antes de iniciar o sistema.'
            ) from _encryption_error
        # Em desenvolvimento, manter compatibilidade sem mascarar o problema em logs.
        print(f'Aviso: chave de criptografia temporária em desenvolvimento: {_encryption_error}', file=sys.stderr)
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

    # Uploads sempre ficam fora de static. Do contrário, /static/ exporia anexos
    # de processos sem passar pela rota autenticada de download.
    UPLOAD_ROOT_FOLDER_NAME = 'uploads'
    PROCESSOS_UPLOAD_SUBFOLDER = 'processos'
    EMPRESA_UPLOAD_SUBFOLDER = 'empresa'
    UPLOAD_ROOT_DIR = os.path.join(DATA_DIR, UPLOAD_ROOT_FOLDER_NAME)
    UPLOAD_PROCESSOS_DIR = os.path.join(UPLOAD_ROOT_DIR, PROCESSOS_UPLOAD_SUBFOLDER)
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


# Migra instalações criadas por versões que usavam static/uploads. A execução
# ocorre durante a carga da configuração, antes de o Flask expor /static/.
_migrate_legacy_public_uploads(
    os.path.join(BASE_DIR, 'static', Config.UPLOAD_ROOT_FOLDER_NAME),
    Config.UPLOAD_ROOT_DIR,
)
