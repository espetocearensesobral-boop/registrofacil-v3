import models


def _csrf_token(client):
    client.get("/login")
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_dashboard_requires_login(app_client):
    response = app_client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_rejects_invalid_csrf(app_client):
    response = app_client.post(
        "/login",
        data={"usuario": "admin", "senha": "admin123", "csrf_token": "invalid"},
    )
    assert response.status_code == 200
    with app_client.session_transaction() as session:
        assert session.get("logado") is not True


def test_login_requires_password_change_on_default_account(app_client):
    models.executar_query(
        "UPDATE usuarios SET must_change_password = 1 WHERE usuario = ?",
        ["admin"],
    )
    response = app_client.post(
        "/login",
        data={
            "usuario": "admin",
            "senha": "admin123",
            "csrf_token": _csrf_token(app_client),
        },
    )
    assert response.status_code == 302
    with app_client.session_transaction() as session:
        assert session.get("logado") is True
        assert session.get("force_password_change") is True

    protected = app_client.get("/dashboard")
    assert protected.status_code == 302
    assert "/perfil" in protected.headers["Location"]
