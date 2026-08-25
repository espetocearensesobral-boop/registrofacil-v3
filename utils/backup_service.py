"""Serviço compartilhado para criação e validação de backups do Registro Fácil."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from config import Config, DATA_DIR
from utils.logger import manutencao_logger as logger

BACKUP_FORMAT_VERSION = 1
MANIFEST_NAME = "backup-manifest.json"
STATUS_FILENAME = ".backup-status.json"
BACKUP_PREFIX = "registrofacil_bkp_"
DEFAULT_RETENTION_COUNT = 14
DEFAULT_ROLLBACK_RETENTION_COUNT = 3


def _sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_archive_name(value: str) -> str:
    """Converte o caminho para o formato POSIX e rejeita traversal."""
    normalized = value.replace(os.sep, "/").replace("\\", "/")
    if normalized.startswith("/") or any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise ValueError(f"Caminho inseguro no backup: {value}")
    return normalized


def _database_snapshot(database_path: str) -> str:
    """Cria um snapshot consistente do SQLite usando a Online Backup API."""
    os.makedirs(Config.TEMP_DIR, exist_ok=True)
    fd, target = tempfile.mkstemp(
        prefix="registrofacil_db_",
        suffix=".db",
        dir=Config.TEMP_DIR,
    )
    os.close(fd)
    source_conn = None
    target_conn = None
    try:
        source_conn = sqlite3.connect(database_path, timeout=30)
        target_conn = sqlite3.connect(target, timeout=30)
        source_conn.backup(target_conn)
        target_conn.commit()
        target_conn.close()
        source_conn.close()
        target_conn = None
        source_conn = None
        if not os.path.isfile(target) or os.path.getsize(target) == 0:
            raise ValueError("O snapshot do banco ficou vazio.")
        check_conn = sqlite3.connect(target, timeout=30)
        try:
            result = check_conn.execute("PRAGMA integrity_check").fetchone()
            if not result or str(result[0]).lower() != "ok":
                raise ValueError(f"Snapshot do banco não passou no integrity_check: {result}")
        finally:
            check_conn.close()
        return target
    except Exception:
        if target_conn is not None:
            target_conn.close()
        if source_conn is not None:
            source_conn.close()
        try:
            os.remove(target)
        except FileNotFoundError:
            pass
        raise


def _add_file(zipf: zipfile.ZipFile, source_path: str, archive_name: str, entries: list[dict]) -> None:
    archive_name = _safe_archive_name(archive_name)
    zipf.write(source_path, archive_name)
    entries.append({
        "path": archive_name,
        "size": os.path.getsize(source_path),
        "sha256": _sha256_file(source_path),
    })


def _add_directory(zipf: zipfile.ZipFile, source_dir: str, archive_root: str, entries: list[dict]) -> None:
    if not os.path.isdir(source_dir):
        raise FileNotFoundError(f"Diretório obrigatório do backup não encontrado: {source_dir}")
    for root, _, filenames in os.walk(source_dir):
        for filename in sorted(filenames):
            source_path = os.path.join(root, filename)
            relative = os.path.relpath(source_path, source_dir)
            _add_file(zipf, source_path, f"{archive_root}/{relative}", entries)


def _key_fingerprints() -> dict[str, str | None]:
    """Registra fingerprints das chaves sem colocar os segredos dentro do ZIP."""
    result = {}
    for name in (".secret_key", ".encryption_key"):
        path = os.path.join(DATA_DIR, name)
        result[name] = _sha256_file(path) if os.path.isfile(path) else None
    return result


def create_backup_archive(
    *,
    destination_dir: str,
    database_path: str,
    upload_processos: str,
    upload_empresa: str,
    log_dir: str,
    source: str = "manual",
) -> dict:
    """Cria, valida e promove atomicamente um backup completo.

    O retorno contém o caminho final, o nome, o SHA-256, o manifesto e as entradas.
    O arquivo temporário nunca recebe o nome definitivo do backup.
    """
    os.makedirs(destination_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = secrets.token_hex(4)
    filename = f"{BACKUP_PREFIX}{timestamp}_{suffix}.zip"
    final_path = os.path.join(destination_dir, filename)
    fd, temp_path = tempfile.mkstemp(prefix=f".{filename}.", suffix=".tmp", dir=destination_dir)
    os.close(fd)
    db_snapshot = None
    entries: list[dict] = []
    try:
        db_snapshot = _database_snapshot(database_path)
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            _add_file(zipf, db_snapshot, f"database/{Path(database_path).name}", entries)
            _add_directory(zipf, upload_processos, "uploads/processos", entries)
            _add_directory(zipf, upload_empresa, "uploads/empresa", entries)
            _add_directory(zipf, log_dir, "logs", entries)
            manifest = {
                "format_version": BACKUP_FORMAT_VERSION,
                "application_version": Config.VERSION,
                "source": source,
                "created_at": datetime.now().astimezone().isoformat(),
                "database": Path(database_path).name,
                "entries": entries,
                "key_fingerprints": _key_fingerprints(),
                "keys_included": False,
            }
            zipf.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"))
        validate_backup_archive(temp_path, require_manifest=True)
        digest = _sha256_file(temp_path)
        os.replace(temp_path, final_path)
        return {
            "path": final_path,
            "filename": filename,
            "sha256": digest,
            "manifest": manifest,
            "size": os.path.getsize(final_path),
        }
    except Exception:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass
        raise
    finally:
        if db_snapshot:
            try:
                os.remove(db_snapshot)
            except FileNotFoundError:
                pass


def stage_backup_restore(archive_path: str, staging_root: str | None = None) -> dict:
    """Extrai um backup validado para staging sem substituir a instalação ativa."""
    validation = validate_backup_archive(archive_path)
    staging_root = staging_root or Config.TEMP_DIR
    os.makedirs(staging_root, exist_ok=True)
    staging_dir = tempfile.mkdtemp(prefix="registrofacil_restore_", dir=staging_root)
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for info in archive.infolist():
                name = _safe_archive_name(info.filename)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise ValueError(f"Link simbólico não permitido no backup: {name}")
                target = os.path.abspath(os.path.join(staging_dir, name))
                if os.path.commonpath([staging_dir, target]) != os.path.abspath(staging_dir):
                    raise ValueError(f"Caminho fora do staging: {name}")
                archive.extract(info, staging_dir)
        database_name = validation["manifest"]["database"]
        staged_database = os.path.join(staging_dir, "database", database_name)
        if not os.path.isfile(staged_database):
            raise ValueError("Banco de dados ausente no backup.")
        connection = sqlite3.connect(staged_database, timeout=30)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
        finally:
            connection.close()
        if not integrity or str(integrity[0]).lower() != "ok":
            raise ValueError(f"Banco restaurado não passou no integrity_check: {integrity}")
        return {
            "staging_dir": staging_dir,
            "database_path": staged_database,
            "manifest": validation["manifest"],
            "sha256": validation["sha256"],
        }
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def promote_staged_restore(
    staged: dict,
    *,
    database_path: str,
    upload_processos: str,
    upload_empresa: str,
    rollback_root: str,
    log_dir: str | None = None,
    preserve_keys: bool = True,
) -> dict:
    """Promove staging validado, mantendo cópia de rollback e sem substituir chaves."""
    if not preserve_keys:
        raise ValueError("A restauração sem preservação de chaves não é permitida.")
    staging_dir = os.path.abspath(staged["staging_dir"])
    if not os.path.isdir(staging_dir):
        raise ValueError("Staging de restauração inexistente.")
    validate_backup_archive(staged.get("archive_path", staged.get("backup_path", ""))) if staged.get("archive_path") else None
    staged_database = os.path.abspath(staged["database_path"])
    if not os.path.isfile(staged_database):
        raise ValueError("Banco restaurado ausente no staging.")
    connection = sqlite3.connect(staged_database, timeout=30)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
    finally:
        connection.close()
    if not integrity or str(integrity[0]).lower() != "ok":
        raise ValueError(f"Banco staged inválido: {integrity}")

    targets = {
        "database": (staged_database, os.path.abspath(database_path), "file"),
        "uploads_processos": (os.path.join(staging_dir, "uploads", "processos"), os.path.abspath(upload_processos), "dir"),
        "uploads_empresa": (os.path.join(staging_dir, "uploads", "empresa"), os.path.abspath(upload_empresa), "dir"),
    }
    if log_dir is not None:
        targets["logs"] = (os.path.join(staging_dir, "logs"), os.path.abspath(log_dir), "dir")
    for label, (source, _, kind) in targets.items():
        if kind == "file" and not os.path.isfile(source):
            raise ValueError(f"Item obrigatório ausente no staging: {label}")
        if kind == "dir" and not os.path.isdir(source):
            raise ValueError(f"Diretório obrigatório ausente no staging: {label}")

    os.makedirs(rollback_root, exist_ok=True)
    rollback_dir = tempfile.mkdtemp(prefix="registrofacil_rollback_", dir=rollback_root)
    moved_dirs: list[tuple[str, str]] = []
    database_rollback = os.path.join(rollback_dir, "database.db")
    try:
        shutil.copy2(database_path, database_rollback)
        for label in ("uploads_processos", "uploads_empresa", "logs"):
            if label not in targets:
                continue
            _, target, _ = targets[label]
            old = os.path.join(rollback_dir, label)
            if os.path.exists(target):
                shutil.move(target, old)
                moved_dirs.append((target, old))
        temp_database = f"{database_path}.restore.tmp"
        shutil.copy2(staged_database, temp_database)
        os.replace(temp_database, database_path)
        for label in ("uploads_processos", "uploads_empresa", "logs"):
            if label not in targets:
                continue
            source, target, _ = targets[label]
            shutil.copytree(source, target)
        return {"rollback_dir": rollback_dir, "database_path": database_path, "keys_preserved": True}
    except Exception:
        try:
            temp_database = f"{database_path}.restore.tmp"
            if os.path.exists(temp_database):
                os.remove(temp_database)
            if os.path.exists(database_rollback):
                shutil.copy2(database_rollback, database_path)
            for target, old in reversed(moved_dirs):
                if os.path.exists(target):
                    shutil.rmtree(target, ignore_errors=True)
                if os.path.exists(old):
                    shutil.move(old, target)
        finally:
            shutil.rmtree(rollback_dir, ignore_errors=True)
        raise


def apply_rollback_retention(rollback_root: str, keep_count: int = DEFAULT_ROLLBACK_RETENTION_COUNT) -> list[str]:
    """Mantém os rollbacks mais recentes e remove somente diretórios reconhecidos."""
    if keep_count < 1:
        raise ValueError("A retenção de rollback precisa manter pelo menos um item.")
    if not os.path.isdir(rollback_root):
        return []
    candidates = [
        entry for entry in os.scandir(rollback_root)
        if entry.is_dir() and entry.name.startswith("registrofacil_rollback_")
    ]
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    removed = []
    for entry in candidates[keep_count:]:
        try:
            shutil.rmtree(entry.path)
            removed.append(entry.path)
        except OSError:
            logger.warning("Falha ao remover rollback antigo: %s", entry.path, exc_info=True)
    return removed


def rollback_promoted_restore(
    rollback_dir: str,
    *,
    database_path: str,
    upload_processos: str,
    upload_empresa: str,
    log_dir: str | None = None,
) -> None:
    """Reverte uma promoção usando o snapshot criado antes da troca."""
    database_backup = os.path.join(rollback_dir, "database.db")
    if not os.path.isfile(database_backup):
        raise ValueError("Rollback sem cópia do banco original.")
    shutil.copy2(database_backup, f"{database_path}.rollback.tmp")
    os.replace(f"{database_path}.rollback.tmp", database_path)
    restore_targets = [
        ("uploads_processos", upload_processos),
        ("uploads_empresa", upload_empresa),
    ]
    if log_dir is not None:
        restore_targets.append(("logs", log_dir))
    for label, target in restore_targets:
        source = os.path.join(rollback_dir, label)
        if os.path.isdir(source):
            if os.path.exists(target):
                shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(source, target)


def write_backup_status(destination_dir: str, *, status: str, source: str, result: dict | None = None, error: str | None = None) -> None:
    """Persiste o último resultado de forma atômica, sem interromper o backup por falha de status."""
    payload = {
        "status": status,
        "source": source,
        "updated_at": datetime.now().astimezone().isoformat(),
        "filename": result.get("filename") if result else None,
        "sha256": result.get("sha256") if result else None,
        "size": result.get("size") if result else None,
        "error": error,
    }
    os.makedirs(destination_dir, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".backup-status.", suffix=".tmp", dir=destination_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, os.path.join(destination_dir, STATUS_FILENAME))
    except Exception:
        try:
            os.remove(temp_path)
        except FileNotFoundError:
            pass
        logger.warning("Não foi possível persistir o status do backup.", exc_info=True)


def read_backup_status(destination_dir: str) -> dict:
    path = os.path.join(destination_dir, STATUS_FILENAME)
    if not os.path.isfile(path):
        return {"status": "never_run", "source": None, "updated_at": None, "filename": None, "sha256": None, "size": None, "error": None}
    try:
        with open(path, "r", encoding="utf-8") as stream:
            payload = json.load(stream)
        return payload if isinstance(payload, dict) else {"status": "invalid"}
    except Exception:
        logger.warning("Status de backup inválido ou ilegível: %s", path, exc_info=True)
        return {"status": "invalid", "source": None, "updated_at": None, "filename": None, "sha256": None, "size": None, "error": "Status ilegível"}


def apply_retention(destination_dir: str, keep_count: int = DEFAULT_RETENTION_COUNT) -> list[str]:
    """Remove somente backups válidos excedentes, preservando o mais recente."""
    if keep_count < 1:
        raise ValueError("A retenção precisa manter pelo menos um backup.")
    candidates = []
    for entry in os.scandir(destination_dir):
        if not entry.is_file() or not entry.name.startswith(BACKUP_PREFIX) or not entry.name.endswith(".zip"):
            continue
        try:
            validate_backup_archive(entry.path, require_entry_integrity=False)
            candidates.append(entry)
        except Exception:
            logger.warning("Backup ignorado pela retenção por não passar na validação: %s", entry.path)
    candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    removed = []
    for entry in candidates[keep_count:]:
        try:
            os.remove(entry.path)
            removed.append(entry.path)
        except OSError:
            logger.warning("Falha ao remover backup antigo: %s", entry.path, exc_info=True)
    return removed


def _sha256_archive_entry(archive: zipfile.ZipFile, name: str) -> str:
    digest = hashlib.sha256()
    with archive.open(name, "r") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_manifest_entries(archive: zipfile.ZipFile, names: list[str], manifest: dict) -> None:
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Manifesto sem lista de entradas.")

    archive_names = set(names)
    declared_names = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Entrada inválida no manifesto.")
        name = _safe_archive_name(str(entry.get("path") or ""))
        if name in declared_names:
            raise ValueError(f"Entrada duplicada no manifesto: {name}")
        if name not in archive_names or name == MANIFEST_NAME:
            raise ValueError(f"Entrada do manifesto ausente no ZIP: {name}")
        declared_names.add(name)

        try:
            expected_size = int(entry["size"])
            expected_sha256 = str(entry["sha256"]).lower()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Metadados inválidos no manifesto para: {name}") from exc
        if expected_size < 0 or len(expected_sha256) != 64:
            raise ValueError(f"Metadados inválidos no manifesto para: {name}")

        info = archive.getinfo(name)
        if info.is_dir() or info.file_size != expected_size:
            raise ValueError(f"Tamanho divergente no backup: {name}")
        actual_sha256 = _sha256_archive_entry(archive, name)
        if not secrets.compare_digest(actual_sha256, expected_sha256):
            raise ValueError(f"Hash divergente no backup: {name}")

    unlisted = (archive_names - {MANIFEST_NAME}) - declared_names
    if unlisted:
        raise ValueError(f"Entrada não declarada no manifesto: {sorted(unlisted)[0]}")

    database_name = _safe_archive_name(f"database/{manifest['database']}")
    if database_name not in declared_names:
        raise ValueError("Manifesto não referencia a entrada do banco de dados.")


def validate_backup_archive(
    path: str,
    *,
    require_manifest: bool = True,
    require_entry_integrity: bool = True,
) -> dict:
    """Valida o ZIP, seus caminhos, o manifesto e a integridade das entradas."""
    with zipfile.ZipFile(path, "r") as archive:
        bad_file = archive.testzip()
        if bad_file:
            raise ValueError(f"Arquivo corrompido dentro do backup: {bad_file}")
        names = archive.namelist()
        for name in names:
            _safe_archive_name(name)
        if require_manifest and MANIFEST_NAME not in names:
            raise ValueError("Backup sem manifesto de integridade.")
        manifest = {}
        if MANIFEST_NAME in names:
            try:
                manifest = json.loads(archive.read(MANIFEST_NAME).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Manifesto de integridade inválido.") from exc
            if not isinstance(manifest, dict):
                raise ValueError("Manifesto de integridade inválido.")
            if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
                raise ValueError("Versão de formato do backup não suportada.")
            if not manifest.get("database"):
                raise ValueError("Manifesto sem referência ao banco de dados.")
            if require_entry_integrity or "entries" in manifest:
                _validate_manifest_entries(archive, names, manifest)
        return {
            "path": path,
            "sha256": _sha256_file(path),
            "size": os.path.getsize(path),
            "manifest": manifest,
            "entries": names,
        }
