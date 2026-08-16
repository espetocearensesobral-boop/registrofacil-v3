import sqlite3

from data import database, migrations


def test_reviews_migration_is_skipped_when_optional_table_is_absent(temp_database):
    with sqlite3.connect(temp_database) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
    assert version == 13


def test_reviews_migration_adds_optional_columns_idempotently(temp_database):
    with sqlite3.connect(temp_database) as connection:
        connection.execute("CREATE TABLE reviews (id INTEGER PRIMARY KEY, body TEXT)")
        connection.execute("PRAGMA user_version = 6")
        connection.commit()

    migrations.executar_migracoes_dados()

    with sqlite3.connect(temp_database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(reviews)")}
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(reviews)")}
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert {"service_id", "service_title", "service_experience"}.issubset(columns)
    assert "reviews_service_id_idx" in indexes
    assert version == 13

    migrations.executar_migracoes_dados()

    with sqlite3.connect(temp_database) as connection:
        columns_after = [row[1] for row in connection.execute("PRAGMA table_info(reviews)")]
    assert columns_after.count("service_id") == 1
