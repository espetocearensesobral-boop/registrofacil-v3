from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_email_defaults_expose_template_aliases_and_notification_policies(temp_database):
    from data.configuration import get_email_config

    config = get_email_config()

    assert config["smtp_encryption"] == "tls"
    assert config["mail_use_tls"] is True
    assert config["mail_use_ssl"] is False
    assert config["mail_server"] == config["smtp_host"]
    assert config["mail_username"] == config["smtp_username"]
    assert config["mail_default_sender"] == config["sender_email"]
    assert config["notify_password_recovery"] == 1
    assert config["notify_deadlines"] == 1
    assert config["notify_backup_failures"] == 1
    assert config["notify_security_events"] == 1


def test_email_schema_and_template_use_canonical_encryption_and_notification_fields():
    schema = read("data/schema.py")
    template = read("templates/configuracoes.html")
    route = read("routes/configuracoes.py")

    for column in (
        "notify_password_recovery",
        "notify_deadlines",
        "notify_backup_failures",
        "notify_security_events",
    ):
        assert column in schema
        assert f'name="{column}"' in template
        assert column in route

    assert "email_config.smtp_encryption == 'tls'" in template
    assert "email_config.smtp_encryption == 'ssl'" in template
    assert "data-email-encryption=\"tls\"" in template
    assert "data-email-encryption=\"ssl\"" in template
    assert "if use_tls and use_ssl" in route


def test_email_notification_columns_exist_after_schema_bootstrap(temp_database):
    import sqlite3

    with sqlite3.connect(temp_database) as connection:
        rows = connection.execute("PRAGMA table_info(email_config)").fetchall()
    columns = {row[1] for row in rows}

    assert {
        "notify_password_recovery",
        "notify_deadlines",
        "notify_backup_failures",
        "notify_security_events",
    }.issubset(columns)



def test_email_checkboxes_are_explicitly_clickable():
    template = read("templates/configuracoes.html")

    assert '#panel-email .cfg-sw input[type="checkbox"]' in template
    assert 'pointer-events: auto !important' in template
    assert 'appearance: auto !important' in template
    assert 'visibility: visible !important' in template
    assert 'cursor: pointer !important' in template


def test_email_test_flow_uses_unsaved_form_values_and_notification_summary():
    route = read("routes/configuracoes.py")

    assert "email_config_override=test_email_config" in route
    assert "Teste SMTP e notificações - Registro Fácil" in route
    assert "Políticas de notificação selecionadas:" in route
    assert "test_password = smtp_password or stored_email_config.get('smtp_password', '')" in route


def test_recovery_link_uses_configured_public_base_url(app_client):
    from routes.auth import construir_link_recuperacao

    flask_app = app_client.application
    flask_app.config["PUBLIC_BASE_URL"] = "http://192.168.0.10:5000"
    with flask_app.test_request_context("/", base_url="http://127.0.0.1:5000"):
        link = construir_link_recuperacao("token-de-teste")

    assert link == "http://192.168.0.10:5000/reset_password/token-de-teste"



def test_discover_lan_ip_prefers_ip_selected_by_udp_route(monkeypatch):
    from utils import network

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def connect(self, address):
            assert address == ("8.8.8.8", 80)

        def getsockname(self):
            return ("192.168.0.25", 5000)

    monkeypatch.setattr(network.socket, "socket", lambda *args, **kwargs: FakeSocket())
    monkeypatch.setattr(network.socket, "gethostbyname", lambda hostname: "127.0.0.1")

    assert network.descobrir_ip_lan() == "192.168.0.25"



def test_discover_lan_ip_falls_back_to_hostname_when_route_is_unavailable(monkeypatch):
    from utils import network

    class FailingSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def connect(self, address):
            raise OSError("rota indisponível")

    monkeypatch.setattr(network.socket, "socket", lambda *args, **kwargs: FailingSocket())
    monkeypatch.setattr(network.socket, "gethostbyname", lambda hostname: "10.0.0.7")

    assert network.descobrir_ip_lan() == "10.0.0.7"



def test_discover_lan_ip_returns_none_without_private_or_public_interface(monkeypatch):
    from utils import network

    class FailingSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def connect(self, address):
            raise OSError("rota indisponível")

    monkeypatch.setattr(network.socket, "socket", lambda *args, **kwargs: FailingSocket())
    monkeypatch.setattr(network.socket, "gethostbyname", lambda hostname: "169.254.10.20")

    assert network.descobrir_ip_lan() is None



def test_recovery_link_uses_discovered_lan_ip_for_loopback_request(monkeypatch, app_client):
    from routes import auth
    from routes.auth import construir_link_recuperacao

    flask_app = app_client.application
    flask_app.config["PUBLIC_BASE_URL"] = ""
    monkeypatch.setattr(auth, "descobrir_ip_lan", lambda: "192.168.0.25")

    with flask_app.test_request_context("/", base_url="http://127.0.0.1:5000"):
        link = construir_link_recuperacao("token-lan")

    assert link == "http://192.168.0.25:5000/reset_password/token-lan"



def test_recovery_link_keeps_non_loopback_request_host(monkeypatch, app_client):
    from routes import auth
    from routes.auth import construir_link_recuperacao

    flask_app = app_client.application
    flask_app.config["PUBLIC_BASE_URL"] = ""
    monkeypatch.setattr(auth, "descobrir_ip_lan", lambda: "192.168.0.25")

    with flask_app.test_request_context("/", base_url="http://10.0.0.8:5000"):
        link = construir_link_recuperacao("token-host")

    assert link == "http://10.0.0.8:5000/reset_password/token-host"


def test_settings_visual_contract_uses_light_tabs_surfaces_and_standard_controls():
    template = read("templates/configuracoes.html")

    assert "border-bottom: 1px solid var(--rf-border-subtle)" in template
    assert "border-radius: 0 !important" in template
    assert "border-bottom-color: var(--rf-accent) !important" in template
    assert "background: var(--rf-surface) !important" in template
    assert "border-radius: var(--rf-radius-sm, 8px) !important" in template
    assert "background: transparent !important" in template
    assert "color-mix(in srgb, var(--rf-surface) 97%, var(--rf-border))" in template
    assert "#F8F8F8 !important" not in template
