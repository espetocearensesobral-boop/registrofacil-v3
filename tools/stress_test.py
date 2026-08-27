"""Teste de estresse isolado para o Registro Fácil.

Uso:
    PYTHONPATH=. python tools/stress_test.py

O script nunca usa a base configurada em produção: todos os dados mutáveis
são redirecionados para um diretório temporário e removidos ao final.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import shutil
import sqlite3
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from statistics import mean

import requests
from bs4 import BeautifulSoup
from werkzeug.security import generate_password_hash
from waitress import create_server

import app as app_module
import models
from config import Config
from data import backup as backup_data
from data import database, migrations, processes, schema
from routes import backup as backup_routes
from utils import logger_config


PASSWORD = "Stress-Test-2026!"
REQUEST_TIMEOUT = 30
USER_COUNTS = (10, 20, 30)
ROUNDS_PER_USER = 5


def _patch_runtime_paths(root: Path) -> Path:
    """Redireciona toda a camada mutável para o sandbox do teste."""
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(data_dir / "stress.db")

    Config.DATA_DIR = str(data_dir)
    Config.DATABASE_PATH = db_path
    Config.SECRET_KEY = "stress-secret-key"
    Config.ENCRYPTION_KEY = Config.ENCRYPTION_KEY
    Config.SESSION_COOKIE_SECURE = False
    Config.MAIL_SUPPRESS_SEND = True
    Config.LOG_DIR = str(data_dir / "logs")
    Config.AUTH_LOG_DIR = str(data_dir / "logs" / "auth")
    Config.OPERACIONAL_LOG_DIR = str(data_dir / "logs" / "operacional")
    Config.SISTEMA_LOG_DIR = str(data_dir / "logs" / "sistema")
    Config.MANUTENCAO_LOG_DIR = str(data_dir / "logs" / "manutencao")
    Config.APP_LOG_DIR = Config.OPERACIONAL_LOG_DIR
    Config.ERROR_LOG_DIR = Config.OPERACIONAL_LOG_DIR
    Config.SECURITY_LOG_DIR = Config.AUTH_LOG_DIR
    Config.BACKUP_ROOT_DIR = str(data_dir / "backups")
    Config.DEFAULT_BACKUP_PATH = Config.BACKUP_ROOT_DIR
    Config.UPLOAD_ROOT_DIR = str(data_dir / "uploads")
    Config.UPLOAD_PROCESSOS_DIR = str(data_dir / "uploads" / "processos")
    Config.EMPRESA_UPLOAD_FOLDER = str(data_dir / "uploads" / "empresa")
    Config.TEMP_DIR = str(data_dir / "temp")

    # Os módulos de logger podem ter sido importados antes do redirecionamento.
    # Remove handlers antigos e recria todos os destinos dentro do sandbox.
    logger_config.LOG_BASE_DIR = Config.LOG_DIR
    logger_config.DOMAIN_DIRS = {
        'auth': Config.AUTH_LOG_DIR,
        'operacional': Config.OPERACIONAL_LOG_DIR,
        'sistema': Config.SISTEMA_LOG_DIR,
        'manutencao': Config.MANUTENCAO_LOG_DIR,
    }
    for logger_name in ('registrofacil.auth', 'registrofacil.operacional', 'registrofacil.sistema', 'registrofacil.manutencao', 'registrofacil_app'):
        runtime_logger = logging.getLogger(logger_name)
        for handler in runtime_logger.handlers[:]:
            runtime_logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    for path in (
        Config.LOG_DIR,
        Config.AUTH_LOG_DIR,
        Config.OPERACIONAL_LOG_DIR,
        Config.SISTEMA_LOG_DIR,
        Config.MANUTENCAO_LOG_DIR,
        Config.BACKUP_ROOT_DIR,
        Config.UPLOAD_PROCESSOS_DIR,
        Config.EMPRESA_UPLOAD_FOLDER,
        Config.TEMP_DIR,
    ):
        Path(path).mkdir(parents=True, exist_ok=True)

    logger_config.setup_all_loggers(console=False)

    for module in (database, migrations, backup_data, processes):
        if hasattr(module, "DATABASE_PATH"):
            module.DATABASE_PATH = db_path
    schema.UPLOAD_FOLDER = Config.UPLOAD_PROCESSOS_DIR
    models.DATABASE_PATH = db_path
    backup_routes.DATABASE_PATH = db_path
    return Path(db_path)


def _create_users(total: int) -> list[dict[str, str]]:
    users = []
    for index in range(total):
        username = f"stress_user_{index + 1:02d}"
        email = f"{username}@stress.local"
        models.create_user(
            f"Usuário de Estresse {index + 1:02d}",
            email,
            username,
            generate_password_hash(PASSWORD),
            role="user",
        )
        users.append({"username": username, "password": PASSWORD})
    models.create_user(
        "Administrador de Estresse",
        "stress_admin@stress.local",
        "stress_admin",
        generate_password_hash(PASSWORD),
        role="admin",
    )
    return users


def _csrf_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    field = soup.find("input", {"name": "csrf_token"})
    if not field or not field.get("value"):
        raise RuntimeError("Token CSRF não encontrado na resposta")
    return field["value"]


def _login(base_url: str, credentials: dict[str, str]) -> tuple[dict[str, str], str]:
    client = requests.Session()
    login_page = client.get(f"{base_url}/login", timeout=REQUEST_TIMEOUT)
    login_page.raise_for_status()
    csrf = _csrf_from_html(login_page.text)
    response = client.post(
        f"{base_url}/login",
        data={
            "usuario": credentials["username"],
            "senha": credentials["password"],
            "csrf_token": csrf,
            "honeypot": "",
        },
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )
    if response.status_code != 200 or "dashboard" not in response.url:
        raise RuntimeError(f"Login falhou para {credentials['username']}: HTTP {response.status_code} {response.url}")

    # GET /logout apenas renderiza a confirmação e disponibiliza um CSRF novo;
    # a sessão continua autenticada até o POST de logout.
    logout_page = client.get(f"{base_url}/logout", timeout=REQUEST_TIMEOUT)
    logout_page.raise_for_status()
    return client.cookies.get_dict(), _csrf_from_html(logout_page.text)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((percentile / 100) * (len(ordered) - 1)))))
    return ordered[index]


def _request_once(base_url: str, cookies: dict[str, str], scenario: str, csrf: str | None = None) -> dict:
    started = time.perf_counter()
    status = None
    error = None
    body = ""
    try:
        if scenario == "dashboard_read":
            response = requests.get(f"{base_url}/dashboard", cookies=cookies, timeout=REQUEST_TIMEOUT)
        elif scenario == "presence_write":
            response = requests.post(
                f"{base_url}/backup/presence/heartbeat",
                cookies=cookies,
                headers={"X-CSRFToken": csrf or "", "X-Requested-With": "XMLHttpRequest"},
                timeout=REQUEST_TIMEOUT,
            )
        elif scenario == "presence_read":
            response = requests.get(
                f"{base_url}/backup/users-presence",
                cookies=cookies,
                headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"},
                timeout=REQUEST_TIMEOUT,
            )
        elif scenario == "health_read":
            response = requests.get(f"{base_url}/api/system/update/health", timeout=REQUEST_TIMEOUT)
        else:
            raise ValueError(f"Cenário desconhecido: {scenario}")
        status = response.status_code
        body = response.text[:500]
        if scenario == "presence_write" and status != 200:
            error = body
        elif scenario in {"dashboard_read", "presence_read", "health_read"} and status != 200:
            error = body
    except Exception as exc:  # noqa: BLE001 - falha deve entrar nas métricas
        error = repr(exc)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {"status": status, "error": error, "elapsed_ms": elapsed_ms, "body": body}


def _process_write_once(
    process_index: int,
    responsible_id: int,
    type_id: int,
    status_id: int,
) -> dict:
    started = time.perf_counter()
    error = None
    try:
        with database.get_sqlite_connection() as connection:
            process_id = processes.create_processo(
                numero_processo=f"STRESS-{int(time.time() * 1000)}-{process_index}",
                titular=f"Titular de Estresse {process_index}",
                titular_telefone="88999990000",
                titular_email=f"titular-{process_index}@stress.local",
                matricula=None,
                tipo_id=type_id,
                data_entrada=datetime.now().strftime("%Y-%m-%d"),
                status_id=status_id,
                prazo_final=datetime.now().strftime("%Y-%m-%d"),
                apresentante=f"Apresentante de Estresse {process_index}",
                apresentante_telefone="88999990001",
                apresentante_email=f"apresentante-{process_index}@stress.local",
                responsavel_id=responsible_id,
                envolvido_notas="stress test",
                observacoes="registro criado pelo baseline de estresse",
                data_conclusao=None,
                possui_matricula=0,
                connection=connection,
            )
        status = "committed" if process_id else "no_id"
    except Exception as exc:  # noqa: BLE001 - falha entra nas métricas
        status = "exception"
        error = repr(exc)
    return {
        "status": status,
        "error": error,
        "elapsed_ms": (time.perf_counter() - started) * 1000,
        "body": "",
    }


def _run_process_write_scenario(
    concurrency: int,
    responsible_ids: list[int],
    type_id: int,
    status_id: int,
    rounds: int,
) -> dict:
    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                _process_write_once,
                index,
                responsible_ids[index % len(responsible_ids)],
                type_id,
                status_id,
            )
            for index in range(concurrency * rounds)
        ]
        for future in as_completed(futures):
            results.append(future.result())
    elapsed_s = max(0.001, time.perf_counter() - started)
    latencies = [item["elapsed_ms"] for item in results]
    errors = [item for item in results if item["error"]]
    status_counts = {}
    for item in results:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1
    return {
        "scenario": "sqlite_process_write",
        "virtual_users": concurrency,
        "requests": len(results),
        "duration_seconds": round(elapsed_s, 3),
        "throughput_rps": round(len(results) / elapsed_s, 2),
        "latency_ms": {
            "mean": round(mean(latencies), 2) if latencies else 0,
            "p50": round(_percentile(latencies, 50), 2),
            "p95": round(_percentile(latencies, 95), 2),
            "p99": round(_percentile(latencies, 99), 2),
            "max": round(max(latencies), 2) if latencies else 0,
        },
        "successes": len(results) - len(errors),
        "errors": len(errors),
        "status_counts": status_counts,
        "error_samples": [item["error"] for item in errors[:5]],
    }


def _run_scenario(
    base_url: str,
    name: str,
    concurrency: int,
    identities: list[tuple[dict[str, str], str | None]],
    rounds: int,
) -> dict:
    started = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for index in range(concurrency):
            cookies, csrf = identities[index % len(identities)]
            scenario = name
            for _ in range(rounds):
                futures.append(executor.submit(_request_once, base_url, cookies, scenario, csrf))
        for future in as_completed(futures):
            results.append(future.result())
    elapsed_s = max(0.001, time.perf_counter() - started)
    latencies = [item["elapsed_ms"] for item in results]
    errors = [item for item in results if item["error"]]
    status_counts = {}
    for item in results:
        key = str(item["status"]) if item["status"] is not None else "exception"
        status_counts[key] = status_counts.get(key, 0) + 1
    return {
        "scenario": name,
        "virtual_users": concurrency,
        "requests": len(results),
        "duration_seconds": round(elapsed_s, 3),
        "throughput_rps": round(len(results) / elapsed_s, 2),
        "latency_ms": {
            "mean": round(mean(latencies), 2) if latencies else 0,
            "p50": round(_percentile(latencies, 50), 2),
            "p95": round(_percentile(latencies, 95), 2),
            "p99": round(_percentile(latencies, 99), 2),
            "max": round(max(latencies), 2) if latencies else 0,
        },
        "successes": len(results) - len(errors),
        "errors": len(errors),
        "status_counts": status_counts,
        "error_samples": [item["error"] for item in errors[:5]],
    }


def _collect_log_lock_errors(root: Path) -> list[str]:
    matches = []
    for path in root.rglob("*.log"):
        try:
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if re.search(r"database is locked|database table is locked|database busy", line, re.I):
                    matches.append(f"{path.name}: {line[-300:]}")
        except OSError:
            continue
    return matches[:20]


def _write_report(report: dict, report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = report_dir / f"stress-baseline-{stamp}.json"
    md_path = report_dir / f"stress-baseline-{stamp}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        f"# Baseline de estresse — Registro Fácil",
        "",
        f"**Data:** {report['timestamp']}",
        f"**Servidor:** Waitress local, {report['waitress_threads']} threads",
        f"**Banco:** SQLite temporário em diretório isolado",
        f"**CPU lógica disponível:** {report['cpu_count']}",
        "",
        "> Este relatório mede o comportamento do servidor e do SQLite em carga controlada. Não representa automaticamente a capacidade de uma máquina Windows diferente; serve como baseline para comparação antes e depois da compilação.",
        "",
        "## Resumo",
        "",
        "| Cenário | Usuários virtuais | Requisições | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Erros |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in report["scenarios"]:
        latency = item["latency_ms"]
        lines.append(
            f"| {item['scenario']} | {item['virtual_users']} | {item['requests']} | {item['throughput_rps']} | {latency['p50']} | {latency['p95']} | {latency['p99']} | {item['errors']} |"
        )
    lines += [
        "",
        "## Critérios de leitura",
        "",
        "A coluna P95 mostra a latência abaixo da qual 95% das requisições terminaram. Erros HTTP, exceções de rede e respostas com status diferente do esperado entram na coluna de erros. Locks SQLite foram procurados tanto nas respostas quanto nos logs temporários.",
        "",
        f"**Locks encontrados:** {len(report['lock_errors'])}",
        "",
        "## Próximo passo",
        "",
        "Repetir o mesmo roteiro em Windows, após gerar o executável, e comparar P95/P99, erros e locks. O teste de produção deve ser feito fora do horário operacional e com uma cópia descartável do banco.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main() -> int:
    started_at = datetime.now().isoformat(timespec="seconds")
    temp_root = Path(tempfile.mkdtemp(prefix="registrofacil-stress-"))
    server = None
    server_thread = None
    try:
        db_path = _patch_runtime_paths(temp_root)
        app_module.configure_and_start_scheduler = lambda *_args, **_kwargs: None
        application = app_module.create_app()
        application.config.update(TESTING=False, SECRET_KEY="stress-secret-key", SESSION_COOKIE_SECURE=False)
        credentials = _create_users(max(USER_COUNTS))

        server = create_server(application, host="127.0.0.1", port=0, threads=8)
        server_thread = threading.Thread(target=server.run, name="stress-waitress", daemon=True)
        server_thread.start()
        port = server.effective_port
        base_url = f"http://127.0.0.1:{port}"

        # Aguarda o socket responder antes de iniciar os usuários virtuais.
        for _ in range(50):
            try:
                if requests.get(f"{base_url}/api/system/update/health", timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                time.sleep(0.1)
        else:
            raise RuntimeError("Waitress não respondeu ao health-check")

        identities = [_login(base_url, user) for user in credentials]
        admin_identity = _login(base_url, {"username": "stress_admin", "password": PASSWORD})
        responsible_ids = [models.get_user_by_username(user["username"])["id"] for user in credentials]
        type_row = database.executar_query("SELECT id FROM tipos_servico ORDER BY id LIMIT 1", fetch_one=True)
        status_row = database.executar_query("SELECT id FROM status_processo WHERE ativo = 1 ORDER BY id LIMIT 1", fetch_one=True)
        if not type_row or not status_row:
            raise RuntimeError("Tipos de serviço ou status padrão não foram inicializados")
        with sqlite3.connect(db_path) as pragma_conn:
            journal_mode = pragma_conn.execute("PRAGMA journal_mode").fetchone()[0]
            busy_timeout = pragma_conn.execute("PRAGMA busy_timeout").fetchone()[0]

        scenarios = []
        for users in USER_COUNTS:
            selected = identities[:users]
            scenarios.append(_run_scenario(base_url, "dashboard_read", users, selected, ROUNDS_PER_USER))
            scenarios.append(_run_scenario(base_url, "presence_write", users, selected, ROUNDS_PER_USER))
            scenarios.append(_run_scenario(base_url, "presence_read", users, [admin_identity], ROUNDS_PER_USER))
            scenarios.append(
                _run_process_write_scenario(
                    users,
                    responsible_ids[:users],
                    type_row["id"],
                    status_row["id"],
                    ROUNDS_PER_USER,
                )
            )

        scenarios.append(_run_scenario(base_url, "health_read", max(USER_COUNTS), [({}, None)], ROUNDS_PER_USER))
        lock_errors = _collect_log_lock_errors(temp_root)
        report = {
            "timestamp": started_at,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "waitress_threads": 8,
            "database_path": str(db_path),
            "sqlite_journal_mode": str(journal_mode or "unknown"),
            "sqlite_busy_timeout": str(busy_timeout or "unknown"),
            "virtual_user_counts": list(USER_COUNTS),
            "rounds_per_user": ROUNDS_PER_USER,
            "scenarios": scenarios,
            "lock_errors": lock_errors,
            "isolated_database": True,
        }
        json_path, md_path = _write_report(report, Path("reports"))
        print(json.dumps({"json": str(json_path), "markdown": str(md_path), "report": report}, ensure_ascii=False, indent=2))
        return 0
    finally:
        if server is not None:
            server.close()
        if server_thread is not None:
            server_thread.join(timeout=5)
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
