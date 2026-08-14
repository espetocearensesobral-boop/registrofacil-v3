# registrofacil/utils/logger_config.py
# Sistema de Logs Centralizado por Domínio — RegistroFácil
# Criado com rotação diária (TimedRotatingFileHandler) e limpeza automática de 90 dias.

import os
import sys
import logging
import time
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Importação segura do Config (compatível com .exe e script .py)
# ---------------------------------------------------------------------------
try:
    from config import Config
except ImportError:
    # Fallback para quando executado fora do contexto normal
    class _FallbackConfig:
        if getattr(sys, 'frozen', False):
            BASE_DIR = os.path.dirname(sys.executable)
        else:
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        LOG_DIR = os.path.join(BASE_DIR, 'logs')
    Config = _FallbackConfig()

# ---------------------------------------------------------------------------
# Constantes de domínio e caminhos
# ---------------------------------------------------------------------------
LOG_BASE_DIR = Config.LOG_DIR

DOMAIN_DIRS = {
    'auth':        os.path.join(LOG_BASE_DIR, 'auth'),
    'operacional': os.path.join(LOG_BASE_DIR, 'operacional'),
    'sistema':     os.path.join(LOG_BASE_DIR, 'sistema'),
    'manutencao':  os.path.join(LOG_BASE_DIR, 'manutencao'),
}

# Retenção de logs: 90 dias
LOG_RETENTION_DAYS = 90

# Formato padrão: [Timestamp] [Nível] [Módulo] [User_ID] [IP] [Mensagem]
LOG_FORMAT = '[%(asctime)s] [%(levelname)s] [%(module)s] [%(user_id)s] [%(ip)s] %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


# ---------------------------------------------------------------------------
# Filtro dinâmico: injeta user_id e ip em cada entrada de log
# ---------------------------------------------------------------------------
class RequestContextFilter(logging.Filter):
    """
    Injeta metadados de contexto (user_id e ip) nos registros de log.
    Tenta obter os dados do contexto Flask se disponível, senão usa 'SISTEMA'.
    Para injetar dados específicos, use os extras:
        logger.info("mensagem", extra={'user_id': 'admin / ID: 1', 'ip': '127.0.0.1'})
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Só busca do contexto Flask se os campos não foram fornecidos explicitamente
        if not hasattr(record, 'user_id'):
            record.user_id = self._get_user_id()
        if not hasattr(record, 'ip'):
            record.ip = self._get_ip()
        return True

    @staticmethod
    def _get_user_id() -> str:
        try:
            from flask import session, has_request_context
            if has_request_context():
                uid = session.get('usuario_id')
                uname = session.get('usuario_username', 'desconhecido')
                if uid:
                    return f"{uname} / ID: {uid}"
        except Exception:
            pass
        return 'SISTEMA'

    @staticmethod
    def _get_ip() -> str:
        try:
            from flask import request, has_request_context
            if has_request_context():
                # Suporte a proxy reverso
                forwarded = request.headers.get('X-Forwarded-For')
                if forwarded:
                    return forwarded.split(',')[0].strip()
                return request.remote_addr or '0.0.0.0'
        except Exception:
            pass
        return '0.0.0.0'


# ---------------------------------------------------------------------------
# Fábrica de handlers de domínio
# ---------------------------------------------------------------------------
def _create_domain_handler(domain: str, level: int = logging.DEBUG) -> TimedRotatingFileHandler:
    """Cria um TimedRotatingFileHandler para um domínio específico."""
    domain_dir = DOMAIN_DIRS[domain]
    os.makedirs(domain_dir, exist_ok=True)

    log_file = os.path.join(domain_dir, f'{domain}.log')
    handler = TimedRotatingFileHandler(
        filename=log_file,
        when='midnight',
        interval=1,
        backupCount=0,      # Sem limite interno; a limpeza é feita pela rotina de 90 dias
        encoding='utf-8',
        utc=False
    )
    handler.suffix = '%Y-%m-%d'
    handler.setLevel(level)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    handler.setFormatter(formatter)

    ctx_filter = RequestContextFilter()
    handler.addFilter(ctx_filter)

    return handler


# ---------------------------------------------------------------------------
# Configuração dos loggers de domínio
# ---------------------------------------------------------------------------
def _setup_domain_logger(name: str, domain: str, level: int = logging.DEBUG,
                          console: bool = False) -> logging.Logger:
    """Configura e retorna um logger para o domínio especificado."""
    logger = logging.getLogger(f'registrofacil.{name}')
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger  # Já configurado (evita duplicação em reloads)

    handler = _create_domain_handler(domain, level)
    logger.addHandler(handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        )
        console_handler.addFilter(RequestContextFilter())
        logger.addHandler(console_handler)

    return logger


def setup_all_loggers(console: bool = True):
    """
    Inicializa todos os loggers de domínio.
    Deve ser chamada uma única vez na inicialização da aplicação.

    Retorna um dict com os loggers prontos para uso:
        {
            'auth':        logger de autenticação e controle de acesso,
            'operacional': logger de operações de cadastro/edição/exclusão,
            'sistema':     logger de inicialização, BD, FTS5 e scheduler,
            'manutencao':  logger de backup e testes de permissão,
        }
    """
    # Garante que os diretórios existem
    for domain_dir in DOMAIN_DIRS.values():
        os.makedirs(domain_dir, exist_ok=True)

    loggers = {
        'auth':        _setup_domain_logger('auth',        'auth',        logging.DEBUG, console=console),
        'operacional': _setup_domain_logger('operacional', 'operacional', logging.DEBUG, console=False),
        'sistema':     _setup_domain_logger('sistema',     'sistema',     logging.DEBUG, console=console),
        'manutencao':  _setup_domain_logger('manutencao',  'manutencao',  logging.DEBUG, console=False),
    }

    loggers['sistema'].info(
        "Sistema de logs inicializado com segregação por domínio.",
        extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
    )
    return loggers


# ---------------------------------------------------------------------------
# Acesso global aos loggers (atalhos para importação direta)
# ---------------------------------------------------------------------------
def get_auth_logger() -> logging.Logger:
    """Logger para eventos de autenticação, login, acesso negado."""
    return logging.getLogger('registrofacil.auth')

def get_operacional_logger() -> logging.Logger:
    """Logger para inconsistências de cadastro, edição e exclusão."""
    return logging.getLogger('registrofacil.operacional')

def get_sistema_logger() -> logging.Logger:
    """Logger para inicialização, tabelas, índices FTS5 e scheduler."""
    return logging.getLogger('registrofacil.sistema')

def get_manutencao_logger() -> logging.Logger:
    """Logger para backup e testes de permissão de escrita."""
    return logging.getLogger('registrofacil.manutencao')


# ---------------------------------------------------------------------------
# Rotina de limpeza automática (90 dias)
# ---------------------------------------------------------------------------
def limpar_logs_antigos(retention_days: int = LOG_RETENTION_DAYS,
                         base_dir: str = None) -> dict:
    """
    Percorre todas as subpastas de log e remove arquivos com data de
    modificação superior a `retention_days` dias.

    Pode ser chamada pelo scheduler.py ou na inicialização do app.py.

    Args:
        retention_days: Número de dias de retenção (padrão: 90).
        base_dir:       Diretório raiz dos logs (padrão: Config.LOG_DIR).

    Returns:
        dict com estatísticas: {'removidos': int, 'erros': int, 'verificados': int}
    """
    _logger = get_sistema_logger()
    base = base_dir or LOG_BASE_DIR
    corte = datetime.now() - timedelta(days=retention_days)
    stats = {'removidos': 0, 'erros': 0, 'verificados': 0}

    _logger.info(
        f"Iniciando limpeza de logs com retenção de {retention_days} dias. "
        f"Corte: {corte.strftime('%Y-%m-%d %H:%M:%S')}. Base: {base}",
        extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
    )

    if not os.path.isdir(base):
        _logger.warning(
            f"Diretório base de logs não encontrado: {base}",
            extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
        )
        return stats

    for root, dirs, files in os.walk(base):
        # Pula arquivos temporários e de permissão gerados pela config
        dirs[:] = [d for d in dirs if d not in ['__pycache__']]

        for filename in files:
            filepath = os.path.join(root, filename)

            # Processa apenas arquivos .log e logs rotacionados (ex: .log.2024-01-01)
            if not (filename.endswith('.log') or '.log.' in filename):
                continue
            # Não remove o arquivo de log ativo (sem data no sufixo)
            # Os rotacionados têm sufixo tipo "auth.log.2024-01-15"
            if '.' not in filename.split('.log')[-1].lstrip('.') and not filename.endswith('.log'):
                continue

            stats['verificados'] += 1

            try:
                mtime = os.path.getmtime(filepath)
                data_modificacao = datetime.fromtimestamp(mtime)

                if data_modificacao < corte:
                    os.remove(filepath)
                    stats['removidos'] += 1
                    _logger.debug(
                        f"Log removido (modificado em {data_modificacao.strftime('%Y-%m-%d')}): {filepath}",
                        extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
                    )
            except OSError as e:
                stats['erros'] += 1
                _logger.error(
                    f"Erro ao remover log antigo '{filepath}': {e}",
                    extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
                )

    _logger.info(
        f"Limpeza de logs concluída. Verificados: {stats['verificados']}, "
        f"Removidos: {stats['removidos']}, Erros: {stats['erros']}.",
        extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
    )
    return stats


# ---------------------------------------------------------------------------
# Compatibilidade retroativa: logger único para módulos legados
# ---------------------------------------------------------------------------
# Mantém o comportamento anterior de `from utils.logger import logger`
# Módulos antigos que usam `logger` genérico passam a gravar em 'operacional'.
# Recomenda-se migrar progressivamente para os loggers específicos de domínio.

def _build_legacy_logger() -> logging.Logger:
    """Cria o logger legado 'registrofacil_app' apontando para 'operacional'."""
    legacy = logging.getLogger('registrofacil_app')
    if not legacy.handlers:
        legacy.setLevel(logging.DEBUG)
        legacy.propagate = False
        handler = _create_domain_handler('operacional', logging.DEBUG)
        legacy.addHandler(handler)
        # Console para o logger legado
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
        ch.addFilter(RequestContextFilter())
        legacy.addHandler(ch)
    return legacy
