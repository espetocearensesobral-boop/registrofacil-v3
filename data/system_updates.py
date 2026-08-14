"""Controle persistente do ciclo de atualização do RegistroFácil.

Esta primeira etapa controla detecção, estado e lock. A substituição física dos
arquivos ficará a cargo de um launcher externo, que será integrado depois que
o fluxo de manutenção estiver validado.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from config import Config
from data.database import get_sqlite_connection
from utils.logger import manutencao_logger

STATE_KEY = "system_update_state"

IDLE_STATE = {
    "state": "idle",
    "version_from": Config.VERSION,
    "version_to": None,
    "progress": 0,
    "message": "Sistema operacional.",
    "error": None,
    "reload_required": False,
    "can_cancel": False,
    "updated_at": None,
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_state(raw: str | None) -> dict[str, Any]:
    if not raw:
        state = dict(IDLE_STATE)
    else:
        try:
            state = {**IDLE_STATE, **json.loads(raw)}
        except (TypeError, ValueError, json.JSONDecodeError):
            state = dict(IDLE_STATE)
    state["updated_at"] = state.get("updated_at") or _now()
    return state


def _ensure_config_row(conn: sqlite3.Connection, key: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO configuracoes (chave, valor, updated_at) "
        "VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))",
        (key, None),
    )


def get_update_state() -> dict[str, Any]:
    with get_sqlite_connection() as conn:
        _ensure_config_row(conn, STATE_KEY)
        row = conn.execute(
            "SELECT valor FROM configuracoes WHERE chave = ?", (STATE_KEY,)
        ).fetchone()
        return _normalize_state(row[0] if row else None)


def _write_state(conn: sqlite3.Connection, state: dict[str, Any]) -> dict[str, Any]:
    state = {**IDLE_STATE, **state, "updated_at": _now()}
    _ensure_config_row(conn, STATE_KEY)
    conn.execute(
        "UPDATE configuracoes SET valor = ?, updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE chave = ?",
        (json.dumps(state, ensure_ascii=False), STATE_KEY),
    )
    return state


def update_state(**changes: Any) -> dict[str, Any]:
    with get_sqlite_connection() as conn:
        current = get_update_state_from_connection(conn)
        return _write_state(conn, {**current, **changes})


def get_update_state_from_connection(conn: sqlite3.Connection) -> dict[str, Any]:
    _ensure_config_row(conn, STATE_KEY)
    row = conn.execute(
        "SELECT valor FROM configuracoes WHERE chave = ?", (STATE_KEY,)
    ).fetchone()
    return _normalize_state(row[0] if row else None)


def compare_versions(left: str, right: str) -> int:
    def parts(value: str) -> tuple[int, ...]:
        cleaned = str(value).strip().lstrip("vV")
        numbers = []
        for item in cleaned.split("."):
            number = "".join(char for char in item if char.isdigit())
            numbers.append(int(number or 0))
        return tuple(numbers or [0])

    left_parts, right_parts = parts(left), parts(right)
    size = max(len(left_parts), len(right_parts))
    left_parts += (0,) * (size - len(left_parts))
    right_parts += (0,) * (size - len(right_parts))
    return (left_parts > right_parts) - (left_parts < right_parts)


def detect_available_version() -> dict[str, Any]:
    """Detecta uma versão informada pelo distribuidor local.

    A integração remota assinada será adicionada na etapa do launcher. Para
    homologação, REGISTROFACIL_UPDATE_VERSION funciona como manifesto local.
    """
    import os

    candidate = os.environ.get("REGISTROFACIL_UPDATE_VERSION", "").strip()
    if not candidate or compare_versions(candidate, Config.VERSION) <= 0:
        return {
            "available": False,
            "current_version": Config.VERSION,
            "available_version": None,
            "message": "Nenhuma atualização disponível.",
        }

    state = update_state(
        state="update_available",
        version_from=Config.VERSION,
        version_to=candidate,
        progress=0,
        message=f"A versão {candidate} está disponível.",
        error=None,
        reload_required=False,
        can_cancel=True,
    )
    return {
        "available": True,
        "current_version": Config.VERSION,
        "available_version": candidate,
        "message": state["message"],
    }


def request_confirmation(target_version: str) -> dict[str, Any]:
    """Arma a atualização, sem iniciar troca física de arquivos."""
    with get_sqlite_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = get_update_state_from_connection(conn)
        if current["state"] not in {"idle", "update_available", "failed"}:
            raise RuntimeError("Já existe uma atualização em andamento.")
        if compare_versions(target_version, Config.VERSION) <= 0:
            raise ValueError("A versão informada não é superior à versão instalada.")
        state = _write_state(
            conn,
            {
                **current,
                "state": "awaiting_confirmation",
                "version_from": Config.VERSION,
                "version_to": target_version,
                "progress": 0,
                "message": "Aguardando confirmação do administrador.",
                "error": None,
                "can_cancel": True,
            },
        )
        manutencao_logger.info(
            "Atualização preparada para confirmação: %s -> %s",
            Config.VERSION,
            target_version,
        )
        return state


def set_maintenance_pending() -> dict[str, Any]:
    """Confirma a pausa lógica; o launcher externo concluirá a atualização."""
    with get_sqlite_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = get_update_state_from_connection(conn)
        if current["state"] != "awaiting_confirmation":
            raise RuntimeError("A atualização não está aguardando confirmação.")
        return _write_state(
            conn,
            {
                **current,
                "state": "maintenance_pending",
                "progress": 5,
                "message": "Atualização confirmada. Aguardando o serviço de atualização.",
                "can_cancel": False,
            },
        )


def cancel_update() -> dict[str, Any]:
    with get_sqlite_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        current = get_update_state_from_connection(conn)
        if not current.get("can_cancel"):
            raise RuntimeError("Esta atualização não pode mais ser cancelada.")
        return _write_state(
            conn,
            {
                **IDLE_STATE,
                "message": "Atualização cancelada pelo administrador.",
            },
        )


def is_maintenance_active(state: dict[str, Any] | None = None) -> bool:
    state = state or get_update_state()
    return state.get("state") in {
        "preparing",
        "blocked",
        "downloading",
        "validating",
        "backing_up",
        "migrating",
        "switching",
        "restarting",
        "verifying",
        "maintenance_pending",
    }


def mark_failed(message: str) -> dict[str, Any]:
    return update_state(
        state="failed",
        progress=0,
        message="A atualização falhou.",
        error=message,
        can_cancel=False,
        reload_required=False,
    )


def mark_ready(version: str) -> dict[str, Any]:
    return update_state(
        state="ready",
        version_to=version,
        progress=100,
        message="Atualização concluída. Recarregue a página.",
        error=None,
        reload_required=True,
        can_cancel=False,
    )
