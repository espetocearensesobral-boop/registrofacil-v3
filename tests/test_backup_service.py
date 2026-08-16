import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from utils import backup_service


def _make_database(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE dados (id INTEGER PRIMARY KEY, valor TEXT)")
    conn.execute("INSERT INTO dados (valor) VALUES ('teste')")
    conn.commit()
    conn.close()


def _make_dirs(tmp_path):
    paths = {}
    for name in ("processos", "empresa", "logs"):
        path = tmp_path / name
        path.mkdir()
        (path / f"{name}.txt").write_text(name, encoding="utf-8")
        paths[name] = str(path)
    return paths


def test_create_backup_archive_is_atomic_and_contains_manifest(tmp_path, monkeypatch):
    database = tmp_path / "registrofacil.db"
    _make_database(database)
    dirs = _make_dirs(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setattr(backup_service.Config, "TEMP_DIR", str(tmp_path / "temp"))
    monkeypatch.setattr(backup_service, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(backup_service.Config, "VERSION", "test")

    result = backup_service.create_backup_archive(
        destination_dir=str(tmp_path / "backups"),
        database_path=str(database),
        upload_processos=dirs["processos"],
        upload_empresa=dirs["empresa"],
        log_dir=dirs["logs"],
        source="test",
    )

    archive_path = Path(result["path"])
    assert archive_path.exists()
    assert archive_path.name.startswith("registrofacil_bkp_")
    assert not list(archive_path.parent.glob("*.tmp"))
    assert result["sha256"] == backup_service._sha256_file(archive_path)

    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read(backup_service.MANIFEST_NAME))
        assert manifest["source"] == "test"
        assert manifest["database"] == "registrofacil.db"
        assert "database/registrofacil.db" in archive.namelist()
        assert backup_service.validate_backup_archive(str(archive_path))["sha256"] == result["sha256"]


def test_validate_backup_archive_rejects_unsafe_paths(tmp_path):
    path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../outside.txt", "x")

    with pytest.raises(ValueError, match="Caminho inseguro"):
        backup_service.validate_backup_archive(str(path), require_manifest=False)


def test_validate_backup_archive_requires_manifest(tmp_path):
    path = tmp_path / "without-manifest.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("database/registrofacil.db", "not-a-real-db")

    with pytest.raises(ValueError, match="manifesto"):
        backup_service.validate_backup_archive(str(path))


def test_retention_keeps_only_valid_newest_backups(tmp_path):
    for index in range(3):
        path = tmp_path / f"registrofacil_bkp_20260815_10{index:02d}00_{index}.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                backup_service.MANIFEST_NAME,
                json.dumps({"format_version": 1, "database": "registrofacil.db"}),
            )
        path.touch()
    # O timestamp do arquivo não deve ser a única forma de validar o conteúdo.
    files = sorted(tmp_path.glob("registrofacil_bkp_*.zip"))
    for index, path in enumerate(files):
        path.touch()
        import os
        os.utime(path, (100 + index, 100 + index))

    removed = backup_service.apply_retention(str(tmp_path), keep_count=1)

    assert len(removed) == 2
    assert len(list(tmp_path.glob("registrofacil_bkp_*.zip"))) == 1


def test_rollback_retention_keeps_latest_known_directories(tmp_path):
    import os
    rollback_root = tmp_path / "rollbacks"
    rollback_root.mkdir()
    for index in range(4):
        path = rollback_root / f"registrofacil_rollback_{index}"
        path.mkdir()
        (path / "database.db").write_text(str(index), encoding="utf-8")
        os.utime(path, (100 + index, 100 + index))
    (rollback_root / "nao-remover").mkdir()

    removed = backup_service.apply_rollback_retention(str(rollback_root), keep_count=2)

    assert len(removed) == 2
    assert len(list(rollback_root.glob("registrofacil_rollback_*"))) == 2
    assert (rollback_root / "nao-remover").exists()


def test_stage_backup_restore_validates_database_and_uses_staging(tmp_path, monkeypatch):
    database = tmp_path / "registrofacil.db"
    _make_database(database)
    dirs = _make_dirs(tmp_path)
    monkeypatch.setattr(backup_service.Config, "TEMP_DIR", str(tmp_path / "temp"))
    result = backup_service.create_backup_archive(
        destination_dir=str(tmp_path / "backups"),
        database_path=str(database),
        upload_processos=dirs["processos"],
        upload_empresa=dirs["empresa"],
        log_dir=dirs["logs"],
        source="test",
    )

    staged = backup_service.stage_backup_restore(result["path"], str(tmp_path / "staging"))

    assert Path(staged["staging_dir"]).is_dir()
    assert Path(staged["database_path"]).is_file()
    assert staged["sha256"] == result["sha256"]
    assert Path(staged["staging_dir"]) != tmp_path / "backups"


def test_promote_staged_restore_replaces_data_and_preserves_keys(tmp_path, monkeypatch):
    database = tmp_path / "registrofacil.db"
    _make_database(database)
    dirs = _make_dirs(tmp_path)
    monkeypatch.setattr(backup_service.Config, "TEMP_DIR", str(tmp_path / "temp"))
    result = backup_service.create_backup_archive(
        destination_dir=str(tmp_path / "backups"),
        database_path=str(database),
        upload_processos=dirs["processos"],
        upload_empresa=dirs["empresa"],
        log_dir=dirs["logs"],
        source="test",
    )
    (Path(dirs["processos"]) / "processos.txt").write_text("estado-atual", encoding="utf-8")
    conn = sqlite3.connect(database)
    conn.execute("UPDATE dados SET valor = 'estado-atual'")
    conn.commit()
    conn.close()
    key = tmp_path / "secret.key"
    key.write_text("nao-alterar", encoding="utf-8")

    staged = backup_service.stage_backup_restore(result["path"], str(tmp_path / "staging"))
    promoted = backup_service.promote_staged_restore(
        staged,
        database_path=str(database),
        upload_processos=dirs["processos"],
        upload_empresa=dirs["empresa"],
        rollback_root=str(tmp_path / "rollbacks"),
    )

    restored = sqlite3.connect(database).execute("SELECT valor FROM dados").fetchone()[0]
    assert restored == "teste"
    assert (Path(dirs["processos"]) / "processos.txt").read_text(encoding="utf-8") == "processos"
    assert key.read_text(encoding="utf-8") == "nao-alterar"
    assert Path(promoted["rollback_dir"]).is_dir()


def test_write_backup_status_is_atomic(tmp_path):
    result = {"filename": "backup.zip", "sha256": "abc", "size": 123}

    backup_service.write_backup_status(
        str(tmp_path), status="success_local", source="manual", result=result
    )

    status_path = tmp_path / backup_service.STATUS_FILENAME
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["status"] == "success_local"
    assert payload["filename"] == "backup.zip"
    assert not list(tmp_path.glob(".backup-status.*.tmp"))
