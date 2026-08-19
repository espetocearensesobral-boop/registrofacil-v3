"""Executor independente para backup agendado.

Uso:
    python -m utils.backup_runner

O processo não inicia Flask nem APScheduler. Ele lê a configuração persistida,
adquire um lock exclusivo e executa a mesma rotina usada pelo backup manual.
"""

from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager

from config import Config
from models import DATABASE_PATH, get_backup_config, get_upload_folder, gravar_log, update_last_backup_time
from utils.backup_service import (
    DEFAULT_RETENTION_COUNT,
    apply_retention,
    create_backup_archive,
    validate_backup_archive,
    write_backup_status,
)
from utils.logger import manutencao_logger as logger


@contextmanager
def exclusive_backup_lock(lock_path: str):
    """Impede duas execuções externas simultâneas no mesmo destino."""
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    handle = open(lock_path, "a+")
    try:
        if os.name == "nt":
            import msvcrt
            try:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Já existe uma execução de backup em andamento.") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("Já existe uma execução de backup em andamento.") from exc
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def run_backup(source: str = "external") -> dict:
    config = get_backup_config()
    destination = config.get("local_path") or Config.BACKUP_ROOT_DIR
    retention_raw = os.environ.get("REGISTROFACIL_BACKUP_RETENTION_COUNT", str(DEFAULT_RETENTION_COUNT))
    try:
        retention_count = max(1, int(retention_raw))
    except ValueError:
        retention_count = DEFAULT_RETENTION_COUNT

    lock_path = os.path.join(destination, ".backup-run.lock")
    with exclusive_backup_lock(lock_path):
        try:
            result = create_backup_archive(
                destination_dir=destination,
                database_path=DATABASE_PATH,
                upload_processos=get_upload_folder(),
                upload_empresa=Config.EMPRESA_UPLOAD_FOLDER,
                log_dir=Config.LOG_DIR,
                source=source,
            )
            validate_backup_archive(result["path"])
            removed = apply_retention(destination, keep_count=retention_count)
            write_backup_status(destination, status="success_local", source=source, result=result)
            update_last_backup_time()
            gravar_log(
                "Backup Externo",
                None,
                None,
                "ExternalRunner",
                f"Backup concluído: {result['filename']} | SHA-256: {result['sha256']} | "
                f"Removidos: {len(removed)}",
            )
            return result
        except Exception as exc:
            write_backup_status(destination, status="failed", source=source, error=str(exc))
            logger.exception("Falha no executor externo de backup")
            raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Executa o backup externo do Registro Fácil")
    parser.add_argument("--source", default="external", choices=("external", "scheduled"))
    args = parser.parse_args(argv)
    try:
        result = run_backup(args.source)
        print(f"Backup concluído: {result['path']}\nSHA-256: {result['sha256']}")
        return 0
    except Exception as exc:
        print(f"Falha no backup: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
