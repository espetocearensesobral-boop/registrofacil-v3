from werkzeug.security import generate_password_hash

from data import locks, users


def test_schema_contains_core_tables(temp_database):
    import sqlite3

    with sqlite3.connect(temp_database) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert {"usuarios", "processos", "titulares", "apresentantes"}.issubset(tables)
    assert "representantes" not in tables


def test_user_creation_and_password_reset_token(temp_database):
    assert users.create_user(
        "Usuário de Teste",
        "teste@example.com",
        "usuario-teste",
        generate_password_hash("senha-segura"),
    )
    user = users.get_user_by_username("usuario-teste")
    assert user and user["usuario"] == "usuario-teste"

    short_id = users.create_password_reset_token(user["id"], expires_in_minutes=10)
    token = users.get_password_reset_token(short_id)
    assert token and token["user_id"] == user["id"]
    assert users.mark_password_reset_token_as_used(token["token_id"]) is True
    assert users.get_password_reset_token(short_id) is None


def test_login_attempts_are_blocked_after_limit(temp_database):
    ip = "198.51.100.44"
    for _ in range(5):
        assert users.registrar_tentativa_login(ip, False)
    allowed, message = users.verificar_tentativas_login(ip)
    assert allowed is False
    assert "tentativas" in message.lower()


def test_login_attempts_are_blocked_by_identity_across_ips(temp_database):
    username = "alvo-distribuido"
    for index in range(5):
        assert users.registrar_tentativa_login(
            f"198.51.100.{50 + index}",
            False,
            username=username,
        )

    allowed, message = users.verificar_tentativas_login(
        "203.0.113.99",
        username,
    )
    assert allowed is False
    assert "tentativas" in message.lower()


def test_record_lock_lifecycle(temp_database):
    admin = users.get_user_by_username("admin")
    assert admin
    owner_id = admin["id"]
    assert locks.acquire_lock("processos", 321, owner_id, 15) is True
    assert locks.is_record_locked("processos", 321, owner_id) is None
    assert locks.renew_lock("processos", 321, owner_id, 15)["success"] is True
    assert locks.release_lock("processos", 321, owner_id)["success"] is True
    assert locks.is_record_locked("processos", 321, owner_id) is None
