"""Criptografia de valores sensíveis armazenados no banco."""

from cryptography.fernet import Fernet

from config import Config
from utils.logger import sistema_logger as logger

try:
    _fernet_key = Config.ENCRYPTION_KEY.encode('utf-8')
    _fernet = Fernet(_fernet_key)
    logger.info("Fernet inicializado com ENCRYPTION_KEY do Config.")
except Exception as e:
    logger.critical(
        "ERRO FATAL DE SEGURANÇA: Erro ao inicializar Fernet com "
        f"ENCRYPTION_KEY do Config: {e}. A aplicação não pode continuar "
        "sem uma chave de criptografia válida.",
        exc_info=True,
    )
    raise RuntimeError(
        "Chave de criptografia inválida ou ausente. "
        "Verifique a configuração ENCRYPTION_KEY."
    )


def encrypt(data):
    if data is None:
        return None
    try:
        return _fernet.encrypt(data.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao criptografar dados: {e}", exc_info=True)
        return None


def decrypt(data):
    if data is None:
        return None
    try:
        return _fernet.decrypt(data.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(
            "Erro ao descriptografar dados: "
            f"{e}. Dados podem estar corrompidos ou chave incorreta. "
            "Retornando None.",
            exc_info=True,
        )
        return None
