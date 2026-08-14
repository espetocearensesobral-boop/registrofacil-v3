from datetime import datetime

import models
from werkzeug.security import generate_password_hash


def _regular_user():
    models.executar_query(
        "INSERT INTO usuarios (nome, email, usuario, senha, ativo, role) VALUES (?, ?, ?, ?, ?, ?)",
        [
            "Usuário Teste",
            "teste@example.com",
            "tester",
            generate_password_hash("senha-teste"),
            1,
            "user",
        ],
    )
    return models.executar_query(
        "SELECT id FROM usuarios WHERE usuario = ?",
        ["tester"],
        fetch_one=True,
    )["id"]


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


def test_permission_denial_for_ajax_returns_json_403(app_client):
    user_id = _regular_user()
    _session(app_client, role="user", username="tester")
    with app_client.session_transaction() as session:
        session["usuario_id"] = user_id

    response = app_client.get(
        "/representantes/",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 403
    assert response.is_json
    assert response.json["success"] is False
    assert "permissão" in response.json["message"].lower()


def test_admin_can_reach_representatives_list(app_client):
    _session(app_client, role="admin")

    response = app_client.get("/representantes/")

    assert response.status_code == 200
