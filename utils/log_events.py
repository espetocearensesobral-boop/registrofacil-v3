"""Contrato comum para eventos de log e auditoria do Registro Fácil."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from flask import g, has_request_context, request, session


_SECRET_PATTERNS = re.compile(
    r"(?i)(password|senha|token|secret|api[_-]?key|encryption[_-]?key|cookie)\s*([:=])\s*([^\s,;]+)"
)


def new_event_id() -> str:
    """Retorna um identificador curto e único para reconciliar destinos."""
    return uuid.uuid4().hex[:20]


def request_id() -> str | None:
    """Obtém ou cria um ID por requisição sem gravá-lo na sessão/cookie."""
    if not has_request_context():
        return None
    current = getattr(g, "rf_request_id", None)
    if not current:
        current = request.headers.get("X-Request-ID") or new_event_id()
        g.rf_request_id = current[:80]
    return g.rf_request_id


def current_user_id() -> str:
    if has_request_context():
        user_id = session.get("usuario_id")
        username = session.get("usuario_username")
        if user_id:
            return f"{username or 'desconhecido'} / ID: {user_id}"
    return "SISTEMA"


def current_ip() -> str:
    if has_request_context():
        return request.remote_addr or "0.0.0.0"
    return "0.0.0.0"


def sanitize_text(value: Any, max_length: int = 4000) -> str | None:
    """Remove segredos óbvios e limita campos livres antes do log."""
    if value is None:
        return None
    text = str(value)
    text = _SECRET_PATTERNS.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)
    return text[:max_length]


def sanitize_details(details: Any) -> str | None:
    if details is None:
        return None
    if isinstance(details, dict):
        safe = {str(key): sanitize_text(value) for key, value in details.items()}
        return json.dumps(safe, ensure_ascii=False, sort_keys=True)
    return sanitize_text(details)


def event_extra(
    *,
    event_id: str | None = None,
    domain: str = "sistema",
    event_type: str | None = None,
    entity_id: Any = None,
    user_id: Any = None,
    ip: str | None = None,
    request_id_value: str | None = None,
    details: Any = None,
) -> dict[str, Any]:
    """Monta extras seguros e compatíveis com o formatter central."""
    return {
        "event_id": event_id or new_event_id(),
        "domain": sanitize_text(domain, 64) or "sistema",
        "event_type": sanitize_text(event_type, 120) or "generic",
        "entity_id": sanitize_text(entity_id, 120) if entity_id is not None else "-",
        "request_id": sanitize_text(request_id_value or request_id(), 80) or "-",
        "user_id": sanitize_text(user_id, 160) if user_id is not None else current_user_id(),
        "ip": sanitize_text(ip, 128) if ip is not None else current_ip(),
        "details": sanitize_details(details) or "-",
    }


def emit_event(logger, level: int, message: str, **kwargs: Any) -> str:
    """Emite um evento com metadados uniformes e retorna o event_id."""
    extras = event_extra(**kwargs)
    event_id = extras["event_id"]
    logger.log(level, sanitize_text(message) or "Evento sem mensagem", extra=extras)
    return event_id
