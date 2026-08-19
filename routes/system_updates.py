"""Endpoints administrativos do ciclo de atualização do sistema."""

import os
import shlex
import subprocess
import sys

from flask import Blueprint, current_app, jsonify, request
from config import Config

from data.system_updates import (
    cancel_update,
    detect_available_version,
    get_update_state,
    request_confirmation,
    set_maintenance_pending,
)
from routes.auth import admin_required, login_status_required, verificar_csrf_token

system_updates_bp = Blueprint("system_updates", __name__, url_prefix="/api/system/update")


def _csrf_failure():
    return jsonify(success=False, message="Token CSRF inválido.", type="danger"), 400


def _require_csrf():
    token = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
    return verificar_csrf_token(token)


def start_worker() -> bool:
    """Inicia o worker fora do processo Flask, exceto durante testes."""
    if current_app.testing or os.environ.get("REGISTROFACIL_DISABLE_WORKER") == "true":
        return False
    raw_command = os.environ.get("REGISTROFACIL_UPDATE_WORKER_COMMAND", "").strip()
    if raw_command:
        command = shlex.split(raw_command)
    elif getattr(sys, 'frozen', False):
        command = [sys.executable, '--update-worker']
    else:
        command = [sys.executable, '-m', 'data.update_worker']
    subprocess.Popen(command, close_fds=True)
    return True


@system_updates_bp.get("/health")
def health():
    return jsonify(success=True, status="ok", version=Config.VERSION)


@system_updates_bp.get("/status")
@login_status_required
def status():
    return jsonify(success=True, **get_update_state())


@system_updates_bp.post("/check")
@admin_required
def check():
    if not _require_csrf():
        return _csrf_failure()
    return jsonify(success=True, **detect_available_version())


@system_updates_bp.post("/confirm")
@admin_required
def confirm():
    if not _require_csrf():
        return _csrf_failure()
    payload = request.get_json(silent=True) or request.form
    target_version = str(payload.get("version") or "").strip()
    if not target_version:
        return jsonify(success=False, message="Informe a versão da atualização.", type="danger"), 400
    try:
        state = request_confirmation(target_version)
        state = set_maintenance_pending()
        worker_started = start_worker()
        if worker_started:
            state["message"] = "Atualização iniciada. Aguarde o progresso e não feche o sistema."
        return jsonify(success=True, worker_started=worker_started, **state)
    except ValueError as exc:
        return jsonify(success=False, message=str(exc), type="warning"), 400
    except RuntimeError as exc:
        return jsonify(success=False, message=str(exc), type="warning"), 409


@system_updates_bp.post("/cancel")
@admin_required
def cancel():
    if not _require_csrf():
        return _csrf_failure()
    try:
        return jsonify(success=True, **cancel_update())
    except RuntimeError as exc:
        return jsonify(success=False, message=str(exc), type="warning"), 409
