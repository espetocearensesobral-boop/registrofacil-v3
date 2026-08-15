import sqlite3

import models


def test_legacy_database_upgrade_preserves_data_and_reaches_current_schema(temp_database):
    with sqlite3.connect(temp_database) as connection:
        connection.execute("DROP TABLE representantes")
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

    assert "representantes" in tables
    assert user_version == 7
    assert admin == ("admin", "admin")
