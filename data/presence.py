"""Persistência leve da presença dos usuários autenticados.

A tabela guarda somente o último heartbeat por usuário. O estado online é
calculado por uma janela de atividade, sem manter uma lista de processos ou
expor conteúdo da sessão no frontend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from data.database import executar_query

ONLINE_WINDOW_SECONDS = 120


def touch_user_presence(user_id: int, ip: str | None = None) -> bool:
    """Atualiza o último instante de atividade e o IP observado do usuário."""
    if not user_id:
        return False
    normalized_ip = (str(ip).strip() if ip else None) or None
    rows = executar_query(
        """
        INSERT INTO user_presence (user_id, last_seen_at, last_ip, updated_at)
        VALUES (?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), ?,
                strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        ON CONFLICT(user_id) DO UPDATE SET
            last_seen_at = excluded.last_seen_at,
            last_ip = COALESCE(excluded.last_ip, user_presence.last_ip),
            updated_at = excluded.updated_at
        """,
        [int(user_id), normalized_ip],
    )
    return bool(rows is not None)


def clear_user_presence(user_id: int) -> bool:
    """Remove a presença ativa no logout sem apagar o último IP observado."""
    if not user_id:
        return False
    rows = executar_query(
        """
        UPDATE user_presence
        SET last_seen_at = NULL,
            updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
        WHERE user_id = ?
        """,
        [int(user_id)],
    )
    return bool(rows is not None)


def list_users_presence(online_window_seconds: int = ONLINE_WINDOW_SECONDS) -> list[dict[str, Any]]:
    """Lista usuários e presença sem retornar senha ou dados de sessão."""
    try:
        window = max(30, int(online_window_seconds))
    except (TypeError, ValueError):
        window = ONLINE_WINDOW_SECONDS

    rows = executar_query(
        """
        SELECT
            u.id,
            u.nome,
            u.usuario,
            u.ativo,
            p.last_seen_at,
            p.last_ip,
            CASE
                WHEN u.ativo = 1
                 AND p.last_seen_at IS NOT NULL
                 AND datetime(p.last_seen_at) >= datetime('now', 'localtime', ?)
                THEN 1 ELSE 0
            END AS online
        FROM usuarios u
        LEFT JOIN user_presence p ON p.user_id = u.id
        ORDER BY online DESC, u.ativo DESC, u.nome COLLATE NOCASE ASC
        """,
        [f"-{window} seconds"],
    ) or []

    result = []
    for row in rows:
        result.append(
            {
                "id": row["id"],
                "nome": row["nome"] or "—",
                "usuario": row["usuario"] or "—",
                "ativo": bool(row["ativo"]),
                "online": bool(row["online"]),
                "last_seen_at": row["last_seen_at"],
                "last_ip": row["last_ip"],
            }
        )
    return result


def summarize_presence(users: list[dict[str, Any]]) -> dict[str, int]:
    """Calcula contadores para o cabeçalho do modal."""
    return {
        "total": len(users),
        "online": sum(1 for user in users if user["online"]),
        "offline": sum(1 for user in users if not user["online"]),
    }
