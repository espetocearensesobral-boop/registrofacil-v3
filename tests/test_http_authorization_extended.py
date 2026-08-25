from datetime import datetime

from werkzeug.security import generate_password_hash

import models
def _session(client, role="user", username="admin"):
    with client.session_transaction() as session:
        session.update(
            {
                "logado": True,
                "usuario_id": 1,
                "usuario_username": username,
                "usuario_role": role,
                "session_start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "csrf_token": "test-csrf",
            }
        )


def _create_regular_user():
    models.executar_query(
        """
        INSERT INTO usuarios (nome, email, usuario, senha, ativo, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, 1, 'user', strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """,
        ["Usuário de teste", "teste-autorizacao@example.com", "usuario_teste", generate_password_hash("senha-teste")],
    )
    return models.executar_query(
        "SELECT id FROM usuarios WHERE usuario = ?",
        ["usuario_teste"],
        fetch_one=True,
    )["id"]


def _regular_user_session(client, user_id):
    with client.session_transaction() as session:
        session.update(
            {
                "logado": True,
                "usuario_id": user_id,
                "usuario_username": "usuario_teste",
                "usuario_role": "user",
                "session_epoch": 0,
                "session_start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "csrf_token": "test-csrf",
            }
        )


def test_regular_user_without_process_permission_cannot_access_dashboard(app_client):
    user_id = _create_regular_user()
    _regular_user_session(app_client, user_id)

    response = app_client.get("/dashboard")
    assert response.status_code == 403

    api_response = app_client.get("/dashboard/api/graficos", headers={"Accept": "application/json"})
    assert api_response.status_code == 403
    assert api_response.get_json()["success"] is False


def test_regular_user_without_presenter_permission_cannot_search_presenters(app_client):
    user_id = _create_regular_user()
    _regular_user_session(app_client, user_id)

    response = app_client.get("/apresentantes/api/buscar?q=ab")
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_inactive_account_session_is_cleared(app_client):
    _session(app_client, role="admin")
    models.executar_query(
        "UPDATE usuarios SET ativo = 0 WHERE usuario = ?",
        ["admin"],
    )

    response = app_client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with app_client.session_transaction() as session:
        assert session.get("logado") is not True
        assert session.get("usuario_id") is None
