# utils/startup_auth.py
# Autenticação de senha mestre desativada (v3.16.4).
# Mantido para compatibilidade de imports.

_SENHA_VERIFICADA: str | None = None


def get_senha_startup() -> str | None:
    return _SENHA_VERIFICADA


def verificar_autenticacao_startup() -> bool:
    return True
