import json

import pytest

from data import system_updates
from data.update_config import load_update_settings


CURRENT_VERSION = "3.28.33"
NEXT_VERSION = "3.28.34"


def _login_admin(client):
    with client.session_transaction() as session:
        session.update(
            logado=True,
            usuario_id=1,
            usuario_role="admin",
            usuario_username="admin",
            csrf_token="csrf-test",
        )


def test_external_update_ini_overrides_manifest_urls(tmp_path):
    config_path = tmp_path / "update.ini"
    config_path.write_text(
        "[update]\n"
        "manifest_url = https://primary.example/manifest.json\n"
        "fallback_manifest_url = https://fallback.example/manifest.json\n"
        "timeout_seconds = 9\n",
        encoding="utf-8",
    )

    settings = load_update_settings(config_path)

    assert settings["manifest_url"] == "https://primary.example/manifest.json"
    assert settings["fallback_manifest_url"] == "https://fallback.example/manifest.json"
    assert settings["timeout_seconds"] == 9


def test_fetch_manifest_accepts_valid_payload(monkeypatch):
    payload = {
        "version": "3.25.0",
        "package_url": "https://github.com/example/app.zip",
        "sha256": "a" * 64,
    }

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(system_updates, "urlopen", lambda *_args, **_kwargs: Response())
    manifest = system_updates.fetch_update_manifest(
        {
            "manifest_url": "https://example.com/manifest.json",
            "fallback_manifest_url": "",
            "timeout_seconds": 5,
        }
    )

    assert manifest["version"] == "3.25.0"
    assert manifest["sha256"] == "a" * 64


def test_fetch_manifest_rejects_insecure_package_url(monkeypatch):
    payload = {"version": "3.25.0", "package_url": "http://insecure/app.zip", "sha256": "a" * 64}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr(system_updates, "urlopen", lambda *_args, **_kwargs: Response())
    with pytest.raises(RuntimeError, match="manifesto válido"):
        system_updates.fetch_update_manifest(
            {
                "manifest_url": "https://example.com/manifest.json",
                "fallback_manifest_url": "",
                "timeout_seconds": 5,
            }
        )


def test_update_state_starts_idle(temp_database):
    state = system_updates.get_update_state()

    assert state["state"] == "idle"
    assert state["version_from"] == CURRENT_VERSION
    assert state["progress"] == 0


def test_detect_available_version_persists_state(temp_database, monkeypatch):
    monkeypatch.setenv("REGISTROFACIL_UPDATE_VERSION", NEXT_VERSION)

    result = system_updates.detect_available_version()
    state = system_updates.get_update_state()

    assert result["available"] is True
    assert result["available_version"] == NEXT_VERSION
    assert state["state"] == "update_available"
    assert state["version_to"] == NEXT_VERSION


def test_confirmation_enters_maintenance_pending(temp_database):
    system_updates.request_confirmation(NEXT_VERSION)
    state = system_updates.set_maintenance_pending()

    assert state["state"] == "maintenance_pending"
    assert state["progress"] == 5
    assert system_updates.is_maintenance_active(state) is True


def test_second_confirmation_is_rejected_while_update_is_active(temp_database):
    system_updates.request_confirmation(NEXT_VERSION)
    system_updates.set_maintenance_pending()

    with pytest.raises(RuntimeError, match="atualização em andamento"):
        system_updates.request_confirmation(NEXT_VERSION)


def test_cancel_is_allowed_before_confirmation(temp_database):
    system_updates.request_confirmation(NEXT_VERSION)
    state = system_updates.cancel_update()

    assert state["state"] == "idle"
    assert state["message"] == "Atualização cancelada pelo administrador."


def test_health_check_is_public(app_client):
    response = app_client.get("/api/system/update/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_update_http_status_and_confirmation_require_auth_and_csrf(app_client):
    response = app_client.get("/api/system/update/status")
    assert response.status_code == 302

    _login_admin(app_client)
    status = app_client.get("/api/system/update/status")
    assert status.status_code == 200
    assert status.get_json()["state"] == "idle"

    invalid_csrf = app_client.post(
        "/api/system/update/confirm",
        json={"version": NEXT_VERSION},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert invalid_csrf.status_code == 400

    confirmed = app_client.post(
        "/api/system/update/confirm",
        json={"version": NEXT_VERSION},
        headers={"X-CSRFToken": "csrf-test", "X-Requested-With": "XMLHttpRequest"},
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["state"] == "maintenance_pending"
    assert confirmed.get_json()["worker_started"] is False


def test_mutations_are_blocked_during_maintenance(app_client):
    _login_admin(app_client)
    system_updates.request_confirmation(NEXT_VERSION)
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
