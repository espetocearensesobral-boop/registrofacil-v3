# utils/db_crypto.py
# Criptografia do banco em repouso desativada (v3.16.4).
# A proteção contra alterações durante o uso (db_lock) permanece ativa.
# Mantido para compatibilidade de imports.


def inicializar_cripto(senha: str, db_path: str) -> bool:
    return True


def verificar_senha_correta(senha: str, db_path: str) -> bool:
    return True
