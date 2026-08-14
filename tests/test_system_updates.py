import json

import pytest

from data import system_updates


def _login_admin(client):
    with client.session_transaction() as session:
        session.update(
            logado=True,
            usuario_id=1,
            usuario_role="admin",
            usuario_username="admin",
            csrf_token="csrf-test",
        )


def test_update_state_starts_idle(temp_database):
    state = system_updates.get_update_state()

    assert state["state"] == "idle"
    assert state["version_from"] == "3.18.0"
    assert state["progress"] == 0


def test_detect_available_version_persists_state(temp_database, monkeypatch):
    monkeypatch.setenv("REGISTROFACIL_UPDATE_VERSION", "3.19.0")

    result = system_updates.detect_available_version()
    state = system_updates.get_update_state()

    assert result["available"] is True
    assert result["available_version"] == "3.19.0"
    assert state["state"] == "update_available"
    assert state["version_to"] == "3.19.0"


def test_confirmation_enters_maintenance_pending(temp_database):
    system_updates.request_confirmation("3.19.0")
    state = system_updates.set_maintenance_pending()

    assert state["state"] == "maintenance_pending"
    assert state["progress"] == 5
    assert system_updates.is_maintenance_active(state) is True


def test_second_confirmation_is_rejected_while_update_is_active(temp_database):
    system_updates.request_confirmation("3.19.0")
    system_updates.set_maintenance_pending()

    with pytest.raises(RuntimeError, match="atualização em andamento"):
        system_updates.request_confirmation("3.20.0")


def test_cancel_is_allowed_before_confirmation(temp_database):
    system_updates.request_confirmation("3.19.0")
    state = system_updates.cancel_update()

    assert state["state"] == "idle"
    assert state["message"] == "Atualização cancelada pelo administrador."


def test_update_http_status_and_confirmation_require_auth_and_csrf(app_client):
    response = app_client.get("/api/system/update/status")
    assert response.status_code == 302

    _login_admin(app_client)
    status = app_client.get("/api/system/update/status")
    assert status.status_code == 200
    assert status.get_json()["state"] == "idle"

    invalid_csrf = app_client.post(
        "/api/system/update/confirm",
        json={"version": "3.19.0"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert invalid_csrf.status_code == 400

    confirmed = app_client.post(
        "/api/system/update/confirm",
        json={"version": "3.19.0"},
        headers={"X-CSRFToken": "csrf-test", "X-Requested-With": "XMLHttpRequest"},
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["state"] == "maintenance_pending"


def test_mutations_are_blocked_during_maintenance(app_client):
    _login_admin(app_client)
    system_updates.request_confirmation("3.19.0")
    system_updates.set_maintenance_pending()

    app_client.application.add_url_rule(
        "/_test_mutation", "_test_mutation", lambda: "changed", methods=["POST"]
    )
    response = app_client.post(
        "/_test_mutation",
        json={"value": "must-not-change"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 423
    assert response.get_json()["type"] == "maintenance"
