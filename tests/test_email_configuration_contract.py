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
