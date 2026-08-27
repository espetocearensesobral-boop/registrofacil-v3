from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from typing import Any

from flask import current_app, g, has_request_context, request, session


_SECRET_NAMES = frozenset({
    "password",
    "senha",
    "token",
    "secret",
    "api_key",
    "apikey",
    "encryption_key",
    "cookie",
    "authorization",
    "smtp_password",
    "sftp_password",
})
_SECRET_PATTERNS = re.compile(
    r"(?i)(?P<key>['\"]?(?:password|senha|token|secret|api[_-]?key|encryption[_-]?key|cookie|authorization|smtp[_-]?password|sftp[_-]?password)['\"]?\s*)(?P<sep>[:=])\s*(?P<quote>['\"]?)(?P<value>[^,;\s}\"']+)(?P=quote)"
)
_MAX_DETAILS_DEPTH = 10


def _normalized_secret_name(key: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def _is_secret_key(key: Any) -> bool:
    normalized = _normalized_secret_name(key)
    return normalized in _SECRET_NAMES or normalized.endswith("_password")


def _redact_text_match(match: re.Match[str]) -> str:
    quote = match.group("quote")
    return f"{match.group('key')}{match.group('sep')}{quote}[REDACTED]{quote}"


def new_event_id() -> str:
    """Retorna um identificador curto e único para reconciliar destinos."""
    return uuid.uuid4().hex[:20]


def request_id() -> str | None:
    """Obtém ou cria um ID por requisição sem gravá-lo na sessão/cookie."""
    if not has_request_context():
        return None
    current = getattr(g, "rf_request_id", None)
    if not current:
        supplied = sanitize_text(request.headers.get("X-Request-ID"), 80)
        current = supplied or new_event_id()
        g.rf_request_id = current
    return g.rf_request_id


def remember_event_id(event_id: str) -> None:
    """Guarda o último evento da requisição para correlacionar escritores sequenciais."""
    if has_request_context():
        g.rf_last_event_id = event_id


def last_event_id() -> str | None:
    if has_request_context():
        return getattr(g, "rf_last_event_id", None)
    return None


def current_user_id() -> str:
    if has_request_context():
        user_id = session.get("usuario_id")
        username = session.get("usuario_username")
        if user_id:
            return f"{username or 'desconhecido'} / ID: {user_id}"
    return "SISTEMA"


def current_ip() -> str:
    if has_request_context():
        if current_app.config.get("TRUST_PROXY_HEADERS"):
            forwarded = request.headers.get("X-Forwarded-For", "")
            if forwarded:
                forwarded_ip = forwarded.split(",", 1)[0].strip()
                if forwarded_ip:
                    return sanitize_text(forwarded_ip, 128)
        return sanitize_text(request.remote_addr or "0.0.0.0", 128)
    return "0.0.0.0"


def sanitize_text(value: Any, max_length: int = 4000) -> str | None:
    """Remove segredos óbvios e limita campos livres antes do log."""
    if value is None:
        return None
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = _SECRET_PATTERNS.sub(_redact_text_match, text)
    return text[:max_length]


def _sanitize_structured(value: Any, depth: int = 0) -> Any:
    if depth >= _MAX_DETAILS_DEPTH:
        return "[TRUNCATED]"
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _is_secret_key(key) else _sanitize_structured(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_structured(item, depth + 1) for item in value]
    return sanitize_text(value)


def sanitize_details(details: Any) -> str | None:
    if details is None:
        return None
    if isinstance(details, (Mapping, list, tuple, set)):
        structured = _sanitize_structured(details)
        serialized = json.dumps(structured, ensure_ascii=False, sort_keys=True, default=str)
        return sanitize_text(serialized)
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
