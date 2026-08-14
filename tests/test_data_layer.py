from werkzeug.security import generate_password_hash

from data import locks, representatives, users


def test_schema_contains_core_tables(temp_database):
    import sqlite3

    with sqlite3.connect(temp_database) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert {"usuarios", "processos", "titulares", "apresentantes", "representantes"}.issubset(tables)


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


def test_representative_crud_and_process_history(temp_database):
    representative_id = representatives.executar_query(
        "INSERT INTO representantes (nome, telefone, email) VALUES (?, ?, ?)",
        ["Representante Teste", "(88) 99999-0101", "rep@example.com"],
    )
    assert representative_id
    representative = representatives.get_representante_by_id(representative_id)
    assert representative["nome"] == "Representante Teste"

    assert representatives.editar_representante(
        representative_id,
        "Representante Atualizado",
        "(88) 99999-0102",
        "rep2@example.com",
    )
    assert representatives.get_representante_by_id(representative_id)["nome"] == "Representante Atualizado"
    assert representatives.buscar_representantes_json("Atualizado")
    assert representatives.representante_tem_processos(representative_id) is False


def test_record_lock_lifecycle(temp_database):
    admin = users.get_user_by_username("admin")
    assert admin
    owner_id = admin["id"]
    assert locks.acquire_lock("processos", 321, owner_id, 15) is True
    assert locks.is_record_locked("processos", 321, owner_id) is None
    assert locks.renew_lock("processos", 321, owner_id, 15)["success"] is True
    assert locks.release_lock("processos", 321, owner_id)["success"] is True
    assert locks.is_record_locked("processos", 321, owner_id) is None
