# registrofacil/utils/logger.py
# Módulo de compatibilidade retroativa.
# Todos os módulos que importam `from utils.logger import logger` continuam
# funcionando. Para novos módulos, prefira importar diretamente de logger_config:
#
#   from utils.logger_config import get_auth_logger, get_operacional_logger, ...

from utils.logger_config import (
    setup_all_loggers,
    get_auth_logger,
    get_operacional_logger,
    get_sistema_logger,
    get_manutencao_logger,
    limpar_logs_antigos,
    _build_legacy_logger,
)

# Logger genérico legado → grava em logs/operacional/
# Mantido para não quebrar módulos existentes (models.py, routes/*.py, etc.)
logger = _build_legacy_logger()

# Logger de segurança legado → agora mapeado para 'auth'
security_logger = get_auth_logger()

# Exporta os loggers de domínio para uso direto
auth_logger        = get_auth_logger()
operacional_logger = get_operacional_logger()
sistema_logger     = get_sistema_logger()
manutencao_logger  = get_manutencao_logger()

__all__ = [
    'logger',
    'security_logger',
    'auth_logger',
    'operacional_logger',
    'sistema_logger',
    'manutencao_logger',
    'setup_all_loggers',
    'limpar_logs_antigos',
]
