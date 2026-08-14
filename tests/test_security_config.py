import sqlite3

import pytest

from config import Config
from data import database, migrations
from data.schema import init_db
from routes import auth


def test_forwarded_ip_is_ignored_without_trusted_proxy():
    with _request_context():
        original = Config.TRUST_PROXY_HEADERS
        try:
            Config.TRUST_PROXY_HEADERS = False
            assert auth.get_client_ip() == "127.0.0.1"
            Config.TRUST_PROXY_HEADERS = True
            assert auth.get_client_ip() == "203.0.113.8"
        finally:
            Config.TRUST_PROXY_HEADERS = original


class _request_context:
    def __enter__(self):
        from flask import Flask

        self.app = Flask(__name__)
        self.ctx = self.app.test_request_context(
            "/",
            base_url="http://localhost",
            headers={"X-Forwarded-For": "203.0.113.8"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.ctx.push()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.ctx.pop()


def test_production_requires_initial_admin_password(tmp_path, monkeypatch):
    db_path = tmp_path / "production.db"
    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(Config, "IS_PRODUCTION", True)
    monkeypatch.setattr(Config, "INITIAL_ADMIN_PASSWORD", None)

    with pytest.raises(RuntimeError, match="INITIAL_ADMIN_PASSWORD"):
        init_db(lambda cursor: None, lambda: None)

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'admin'").fetchone()[0] == 0
