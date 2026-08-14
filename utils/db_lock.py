# utils/db_lock.py
# Proteção do arquivo de banco de dados em nível de sistema operacional.
# Enquanto o sistema estiver rodando, o arquivo .db não pode ser
# movido, renomeado ou excluído por processos externos.

import sys
import os
import atexit

_lock_handle = None  # mantemos a referência globalmente para não ser coletada pelo GC

def adquirir_lock_db(db_path: str) -> bool:
    """
    Abre o arquivo de banco de dados com flags que impedem que outro
    processo o exclua ou renomeie enquanto este handle estiver aberto.

    Windows: CreateFileW sem FILE_SHARE_DELETE (flag 0x4).
    Linux/macOS: flock LOCK_SH no descritor.

    Retorna True se o lock foi adquirido, False caso contrário.
    """
    global _lock_handle

    if not os.path.exists(db_path):
        return False  # BD ainda não existe (primeira execução antes do init_db)

    try:
        if sys.platform == "win32":
            _lock_handle = _adquirir_lock_windows(db_path)
        else:
            _lock_handle = _adquirir_lock_unix(db_path)

        if _lock_handle:
            atexit.register(liberar_lock_db)
            return True
        return False

    except Exception as e:
        print(f"[db_lock] Aviso: não foi possível adquirir lock no arquivo DB: {e}")
        return False


def liberar_lock_db():
    """Libera o lock ao encerrar o processo."""
    global _lock_handle
    if _lock_handle is None:
        return
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.CloseHandle(_lock_handle)
        else:
            import fcntl
            fcntl.flock(_lock_handle, fcntl.LOCK_UN)
            _lock_handle.close()
        _lock_handle = None
    except Exception:
        pass


# ── Implementações por plataforma ──────────────────────────────────────────

def _adquirir_lock_windows(db_path: str):
    """
    Abre o arquivo com FILE_SHARE_READ | FILE_SHARE_WRITE (0x3),
    sem FILE_SHARE_DELETE (0x4), impedindo exclusão/renomeação.
    SQLite ainda consegue abrir/escrever normalmente.
    """
    import ctypes
    import ctypes.wintypes

    GENERIC_READ      = 0x80000000
    FILE_SHARE_READ   = 0x00000001
    FILE_SHARE_WRITE  = 0x00000002
    # Intencionalmente SEM FILE_SHARE_DELETE (0x4)
    OPEN_EXISTING     = 3
    FILE_ATTR_NORMAL  = 0x80

    handle = ctypes.windll.kernel32.CreateFileW(
        db_path,
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE,  # sem DELETE
        None,
        OPEN_EXISTING,
        FILE_ATTR_NORMAL,
        None
    )

    INVALID_HANDLE = ctypes.wintypes.HANDLE(-1).value
    if handle == INVALID_HANDLE:
        return None
    return handle


def _adquirir_lock_unix(db_path: str):
    """
    Abre e aplica flock LOCK_SH no arquivo.
    LOCK_SH permite leituras simultâneas (SQLite) mas sinaliza uso ativo.
    """
    import fcntl
    fd = open(db_path, 'rb')
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        return fd
    except OSError:
        fd.close()
        return None
