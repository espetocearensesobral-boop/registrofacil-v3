import sqlite3

import models


def test_representantes_migration_consolidates_and_removes_legacy_data(temp_database):
    with sqlite3.connect(temp_database) as connection:
        connection.execute(
            """CREATE TABLE representantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                telefone TEXT,
                email TEXT,
                ultimo_registro_id INTEGER,
                created_at TEXT,
                updated_at TEXT
            )"""
        )
        connection.execute(
            "INSERT INTO representantes (nome, telefone, email) VALUES (?, ?, ?)",
            ("Pessoa Legada", "88999990000", "legado@example.com"),
        )
        for coluna in ("representante", "representante_telefone", "representante_email"):
            connection.execute(f"ALTER TABLE processos ADD COLUMN {coluna} TEXT")
        connection.execute("PRAGMA user_version = 13")
        connection.commit()

    models.init_db()

    with sqlite3.connect(temp_database) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(processos)")
        }
        row = connection.execute(
            "SELECT nome, telefone, email FROM apresentantes WHERE nome = ?",
            ("Pessoa Legada",),
        ).fetchone()
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert "representantes" not in tables
    assert {"representante", "representante_telefone", "representante_email"}.isdisjoint(columns)
    assert row == ("Pessoa Legada", "88999990000", "legado@example.com")
    assert version == 14
