import pytest

from utils import sftp_backup


def test_validate_sftp_config_requires_complete_and_absolute_values():
    with pytest.raises(ValueError, match="obrigatórios"):
        sftp_backup.validate_sftp_config({"sftp_host": "host"})
    with pytest.raises(ValueError, match="absoluto"):
        sftp_backup.validate_sftp_config({
            "sftp_host": "host",
            "sftp_username": "user",
            "sftp_password": "pass",
            "sftp_remote_path": "relative",
        })


def test_remote_backup_target_rejects_traversal():
    with pytest.raises(ValueError, match="inválido"):
        sftp_backup.remote_backup_target("/backups", "../arquivo.zip")


def test_sftp_connection_checks_directory(monkeypatch):
    class Attrs:
        st_mode = 0o040755

    class FakeSftp:
        def stat(self, path):
            assert path == "/backups"
            return Attrs()

        def close(self):
            pass

    class FakeTransport:
        def __init__(self, address):
            assert address == ("host", 22)

        def connect(self, username, password):
            assert username == "user"
            assert password == "pass"

        def close(self):
            pass

    monkeypatch.setattr(sftp_backup.paramiko, "Transport", FakeTransport)
    monkeypatch.setattr(sftp_backup.paramiko.SFTPClient, "from_transport", lambda _: FakeSftp())

    result = sftp_backup.test_sftp_connection({
        "sftp_host": "host",
        "sftp_port": 22,
        "sftp_username": "user",
        "sftp_password": "pass",
        "sftp_remote_path": "/backups",
    })

    assert result["ok"] is True
    assert result["remote_path"] == "/backups"
