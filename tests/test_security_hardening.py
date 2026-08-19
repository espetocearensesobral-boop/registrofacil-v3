from datetime import datetime

import models


def _authenticated_session(client, role="admin", user_id=1, username="admin", epoch=0):
    with client.session_transaction() as session:
        session.update(
            {
                "logado": True,
                "usuario_id": user_id,
                "usuario_username": username,
                "usuario_role": role,
                "session_epoch": epoch,
                "session_start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "csrf_token": "test-csrf",
            }
        )


def test_titular_create_rejects_missing_csrf_without_mutation(app_client):
    _authenticated_session(app_client)
    before = models.executar_query("SELECT COUNT(*) AS total FROM titulares", fetch_one=True)["total"]

    response = app_client.post(
        "/titulares/novo",
        data={"nome": "Titular sem CSRF", "telefone": "", "email": ""},
    )

    after = models.executar_query("SELECT COUNT(*) AS total FROM titulares", fetch_one=True)["total"]
    assert response.status_code == 200
    assert after == before


def test_apresentante_create_rejects_missing_csrf_without_mutation(app_client):
    _authenticated_session(app_client)
    before = models.executar_query("SELECT COUNT(*) AS total FROM apresentantes", fetch_one=True)["total"]

    response = app_client.post(
        "/apresentantes/novo",
        data={"nome": "Apresentante sem CSRF", "telefone": "", "email": ""},
    )

    after = models.executar_query("SELECT COUNT(*) AS total FROM apresentantes", fetch_one=True)["total"]
    assert response.status_code == 200
    assert after == before


def test_notification_mutation_requires_csrf(app_client):
    _authenticated_session(app_client)

    response = app_client.post("/notificacoes/api/marcar-todas-lidas", json={})

    assert response.status_code == 403
    assert response.get_json()["success"] is False


def test_system_update_check_requires_csrf(app_client):
    _authenticated_session(app_client)

    response = app_client.post("/api/system/update/check")

    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_session_epoch_invalidates_previous_session(app_client):
    _authenticated_session(app_client, epoch=0)
    models.executar_query(
        "UPDATE usuarios SET session_epoch = 1 WHERE id = ?",
        [1],
    )

    response = app_client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with app_client.session_transaction() as session:
        assert session.get("logado") is not True


def test_stale_role_cannot_use_process_search_permission(app_client):
    _authenticated_session(app_client, role="user", epoch=0)

    response = app_client.get("/api/global_search?q=1")

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_invalid_role_is_rejected_at_data_layer(temp_database):
    result = models.create_user(
        "Role inválida",
        "role-invalida@example.com",
        "role-invalida",
        "hash",
        role="root",
    )

    assert result is None
    assert models.get_user_by_username("role-invalida") is None


def test_titular_optimistic_update_rejects_stale_version(temp_database):
    models.executar_query(
        "INSERT INTO titulares (nome, telefone, email, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        ["Titular Concorrência", None, None, "2026-01-01 10:00:00", "2026-01-01 10:00:00"],
    )
    titular = models.executar_query(
        "SELECT id FROM titulares WHERE nome = ?",
        ["Titular Concorrência"],
        fetch_one=True,
    )
    models.executar_query(
        "UPDATE titulares SET updated_at = ? WHERE id = ?",
        ["2026-01-01 11:00:00", titular["id"]],
    )

    try:
        models.editar_titular(
            titular["id"],
            "Titular Concorrência Atualizado",
            None,
            None,
            expected_updated_at="2026-01-01 10:00:00",
        )
    except ValueError as exc:
        assert "alterado por outro usuário" in str(exc)
    else:
        raise AssertionError("A edição obsoleta deveria ser rejeitada")


def test_login_marks_session_permanent(app_client):
    login_page = app_client.get("/login")
    assert login_page.status_code == 200
    with app_client.session_transaction() as session:
        csrf_token = session["csrf_token"]

    response = app_client.post(
        "/login",
        data={"usuario": "admin", "senha": "admin123", "csrf_token": csrf_token},
    )

    assert response.status_code == 302
    with app_client.session_transaction() as session:
        assert session.permanent is True
