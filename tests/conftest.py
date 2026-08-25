from pathlib import Path

import os

os.environ.setdefault('REGISTROFACIL_ENV', 'test')
os.environ.setdefault('INITIAL_ADMIN_PASSWORD', 'pytest-admin-password')

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


@pytest.fixture
def app_client(temp_database, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "configure_and_start_scheduler", lambda *_args, **_kwargs: None)
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True, SECRET_KEY="pytest-secret")
    return flask_app.test_client()
