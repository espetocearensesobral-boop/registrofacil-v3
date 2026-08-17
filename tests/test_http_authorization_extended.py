from datetime import datetime

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
