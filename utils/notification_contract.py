"""Contrato comum para mensagens HTTP e notificações do RegistroFácil."""

from __future__ import annotations

TITLES = {
    "success": "Sucesso",
    "danger": "Erro",
    "warning": "Atenção",
    "info": "Informação",
}


def notification_payload(message: str, kind: str = "info", title: str | None = None, **extra):
    normalized = kind if kind in TITLES else "info"
    payload = {
        "type": normalized,
        "title": title or TITLES[normalized],
        "message": str(message or "").strip() or TITLES[normalized],
    }
    payload.update(extra)
    return payload


def success(message: str, **extra):
    return notification_payload(message, "success", **extra)


def error(message: str, **extra):
    return notification_payload(message, "danger", **extra)


def warning(message: str, **extra):
    return notification_payload(message, "warning", **extra)


def info(message: str, **extra):
    return notification_payload(message, "info", **extra)
