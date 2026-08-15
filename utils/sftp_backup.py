"""Operações seguras e compartilhadas do destino SFTP."""

from __future__ import annotations

import posixpath

import paramiko


def validate_sftp_config(config: dict) -> tuple[str, int, str, str, str]:
    host = str(config.get("sftp_host") or "").strip()
    username = str(config.get("sftp_username") or "").strip()
    password = str(config.get("sftp_password") or "")
    remote_path = str(config.get("sftp_remote_path") or "/backups/").strip()
    try:
        port = int(config.get("sftp_port") or 22)
    except (TypeError, ValueError) as exc:
        raise ValueError("A porta SFTP precisa ser numérica.") from exc
    if not host or not username or not password or not remote_path:
        raise ValueError("Host, usuário, senha e caminho remoto são obrigatórios.")
    if not 1 <= port <= 65535:
        raise ValueError("A porta SFTP deve estar entre 1 e 65535.")
    if "\x00" in remote_path or not remote_path.startswith("/"):
        raise ValueError("O caminho remoto SFTP precisa ser absoluto e válido.")
    return host, port, username, password, remote_path


def test_sftp_connection(config: dict) -> dict:
    """Autentica, verifica o diretório remoto e retorna metadados não sensíveis."""
    host, port, username, password, remote_path = validate_sftp_config(config)
    transport = None
    sftp = None
    try:
        transport = paramiko.Transport((host, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        attrs = sftp.stat(remote_path)
        if not (attrs.st_mode & 0o040000):
            raise ValueError("O caminho remoto informado não é um diretório.")
        return {
            "ok": True,
            "host": host,
            "port": port,
            "remote_path": remote_path,
            "message": "Conexão SFTP e diretório remoto validados com sucesso.",
        }
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Falha ao conectar ou acessar o diretório SFTP: {exc}") from exc
    finally:
        if sftp is not None:
            sftp.close()
        if transport is not None:
            transport.close()


def remote_backup_target(remote_path: str, filename: str) -> str:
    """Monta caminho POSIX do arquivo remoto sem aceitar traversal no nome."""
    if filename != posixpath.basename(filename) or filename in {"", ".", ".."}:
        raise ValueError("Nome de arquivo remoto inválido.")
    return posixpath.join(remote_path.rstrip("/"), filename)
