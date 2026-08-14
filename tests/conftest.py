from pathlib import Path

import pytest

from data import backup, database, migrations, processes
import models


@pytest.fixture
def temp_database(tmp_path, monkeypatch):
    db_path = Path(tmp_path) / "registrofacil-test.db"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(backup, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(processes, "DATABASE_PATH", str(db_path))
    models.init_db()
    return db_path
