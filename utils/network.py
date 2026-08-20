"""Utilitários de rede usados pelo servidor central do Registro Fácil."""

from __future__ import annotations

import socket


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


def descobrir_ip_lan() -> str | None:
    """Descobre o IPv4 local escolhido pela rota principal da máquina.

    A conexão UDP é usada apenas para consultar a interface/rota escolhida pelo
    sistema operacional; não há conexão TCP nem envio de dados ao destino.
    """
    candidatos: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            candidatos.append(sock.getsockname()[0])
    except OSError:
        pass

    try:
        candidatos.append(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass

    for candidato in candidatos:
        if candidato and candidato not in LOOPBACK_HOSTS and not candidato.startswith("169.254."):
            return candidato
    return None
