from datetime import datetime, timedelta

import models


def _authenticated_session(client, role="user", username="admin"):
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


def test_session_is_invalidated_after_new_login_timestamp(app_client):
    _authenticated_session(app_client, role="admin")
    invalidation_time = (datetime.now() + timedelta(seconds=30)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    models.executar_query(
        "UPDATE usuarios SET session_invalidate_at = ? WHERE usuario = ?",
        [invalidation_time, "admin"],
    )

    response = app_client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with app_client.session_transaction() as session:
        assert session.get("logado") is not True


def test_regular_user_cannot_access_admin_route(app_client):
    _authenticated_session(app_client, role="user")

    response = app_client.get("/permissoes/usuario/1")

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]
