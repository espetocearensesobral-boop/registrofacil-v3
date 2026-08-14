"""Worker externo do processo de atualização.

O worker pode ser iniciado pelo supervisor da instalação. Ele não roda dentro
da requisição Flask e, por padrão, para em `ready_to_restart` quando não existe
um comando explícito de reinício configurado.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from config import Config
from data.system_updates import (
    fetch_update_manifest,
    get_update_state,
    mark_failed,
    mark_ready,
    update_state,
)
from data.update_launcher import (
    backup_installation,
    get_release_layout,
    prepare_release,
    activate_release,
    run_progress_state,
)


def _restart_command() -> list[str] | None:
    raw = os.environ.get("REGISTROFACIL_RESTART_COMMAND", "").strip()
    return shlex.split(raw) if raw else None


def _health_url() -> str:
    return os.environ.get("REGISTROFACIL_HEALTH_URL", "http://127.0.0.1:5000/api/system/health")


def _wait_for_health(timeout: int = 60) -> bool:
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(_health_url(), timeout=3) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def _restart_and_wait(command: list[str]) -> bool:
    subprocess.Popen(command, close_fds=True)
    return _wait_for_health()


def run_update() -> dict[str, Any]:
    state = get_update_state()
    if state.get("state") != "maintenance_pending":
        raise RuntimeError("O sistema não está aguardando execução de atualização.")

    manifest = state.get("manifest") or fetch_update_manifest()
    version = str(manifest.get("version", "")).strip()
    layout = get_release_layout()
    update_state(state="preparing", progress=8, message="Preparando atualização...")

    try:
        backup = backup_installation(
            layout,
            Config.DATABASE_PATH,
            Config.UPLOAD_ROOT_DIR,
            (Path(Config.DATA_DIR) / ".secret_key", Path(Config.DATA_DIR) / ".encryption_key"),
        )
        update_state(
            state="backing_up",
            progress=20,
            message="Backup concluído. Preparando o pacote...",
            backup_path=str(backup),
        )
        release = prepare_release(manifest, layout, progress=run_progress_state)
        update_state(
            state="switching",
            progress=90,
            message="Release validada e pronta para ativação.",
            release_path=str(release),
        )

        command = _restart_command()
        if not command:
            return update_state(
                state="ready_to_restart",
                progress=95,
                message="Atualização preparada. Configure REGISTROFACIL_RESTART_COMMAND para reiniciar o serviço.",
                can_cancel=False,
                reload_required=False,
            )

        activate_release(layout, version)
        update_state(state="restarting", progress=96, message="Reiniciando o serviço...")
        if not _restart_and_wait(command):
            raise RuntimeError("O health check não respondeu após o reinício.")
        return mark_ready(version)
    except Exception as exc:
        return mark_failed(str(exc))


def main() -> int:
    try:
        result = run_update()
        return 0 if result.get("state") in {"ready", "ready_to_restart"} else 1
    except Exception as exc:
        mark_failed(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
