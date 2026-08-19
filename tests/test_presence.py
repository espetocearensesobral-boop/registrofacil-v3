from data.presence import clear_user_presence, list_users_presence, touch_user_presence


def _session(client, role="admin"):
    with client.session_transaction() as session:
        session.update(
            {
                "logado": True,
                "usuario_id": 1,
                "usuario_nome": "Administrador",
                "usuario_username": "admin",
                "usuario_role": role,
                "session_epoch": 0,
                "csrf_token": "presence-csrf",
            }
        )


def test_presence_is_recorded_and_listed_for_admin(app_client):
    _session(app_client)
    touch_user_presence(1, "192.168.0.25")

    response = app_client.get(
        "/backup/users-presence",
        environ_base={"REMOTE_ADDR": "192.168.0.25"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["summary"]["online"] == 1
    admin = next(user for user in payload["users"] if user["usuario"] == "admin")
    assert admin["online"] is True
    assert admin["last_ip"] == "192.168.0.25"
    assert "senha" not in admin
    assert "session_epoch" not in admin


def test_logout_clears_online_state_but_keeps_last_ip(temp_database):
    touch_user_presence(1, "10.0.0.15")
    assert list_users_presence()[0]["online"] is True

    clear_user_presence(1)
    admin = next(user for user in list_users_presence() if user["usuario"] == "admin")
    assert admin["online"] is False
    assert admin["last_ip"] == "10.0.0.15"


def test_presence_endpoint_requires_administrative_session(app_client):
    _session(app_client, role="user")

    response = app_client.get("/backup/users-presence")

    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_presence_heartbeat_requires_csrf_and_updates_ip(app_client):
    _session(app_client)

    invalid = app_client.post(
        "/backup/presence/heartbeat",
        headers={"X-Requested-With": "XMLHttpRequest", "X-CSRFToken": "invalid"},
    )
    assert invalid.status_code == 400

    valid = app_client.post(
        "/backup/presence/heartbeat",
        headers={
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": "presence-csrf",
        },
    )
    assert valid.status_code == 200
    assert valid.get_json()["success"] is True


def test_backup_page_renders_presence_modal_for_admin(app_client):
    _session(app_client)

    response = app_client.get("/backup/")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "backupUsersPresenceModal" in html
    assert "Usuários na rede" in html
    assert "/backup/users-presence" in html
