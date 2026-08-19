import sqlite3

import models


def test_legacy_database_upgrade_preserves_data_and_reaches_current_schema(temp_database):
    with sqlite3.connect(temp_database) as connection:
        connection.execute("PRAGMA user_version = 0")
        connection.commit()

    models.init_db()

    with sqlite3.connect(temp_database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        user_version = connection.execute("PRAGMA user_version").fetchone()[0]
        admin = connection.execute(
            "SELECT usuario, role FROM usuarios WHERE usuario = ?",
            ["admin"],
        ).fetchone()

    assert "representantes" not in tables
    assert user_version == 14
    assert admin == ("admin", "admin")


def test_init_db_clears_legacy_uploads_path_without_lock(temp_database):
    models.executar_query(
        "UPDATE backup_configs SET uploads_path = ? WHERE id = (SELECT id FROM backup_configs LIMIT 1)",
        ["C:/legacy/uploads/processos"],
    )

    models.init_db()

    config = models.executar_query(
        "SELECT uploads_path FROM backup_configs LIMIT 1",
        fetch_one=True,
    )
    assert config["uploads_path"] is None


def test_init_db_quotes_theme_default_with_hyphen(tmp_path, monkeypatch):
    db_path = tmp_path / "legacy-theme.db"
    from data import database, migrations, backup, processes

    monkeypatch.setattr(database, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(migrations, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(backup, "DATABASE_PATH", str(db_path))
    monkeypatch.setattr(processes, "DATABASE_PATH", str(db_path))

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL UNIQUE,
                tema TEXT DEFAULT 'light',
                notificacoes_push INTEGER DEFAULT 1,
                notificacoes_email INTEGER DEFAULT 1,
                dashboard_layout TEXT,
                filtros_salvos TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        connection.commit()

    models.init_db()

    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO user_preferences (usuario_id) VALUES (1)")
        theme = connection.execute(
            "SELECT tema_cor FROM user_preferences WHERE usuario_id = 1"
        ).fetchone()[0]

    assert theme == "paleta-01"
