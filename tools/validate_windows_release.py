"""Valida contratos estáticos da distribuição Windows antes da compilação."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def main() -> int:
    config = read("config.py")
    build = read("BUILD_WINDOWS.bat")
    installer = read("INSTALADOR_RegistroFacil.iss")
    requirements_build = read("requirements-build.txt")
    worker = read("data/update_worker.py")
    app = read("app.py")

    version_match = re.search(r"VERSION\s*=\s*['\"]([^'\"]+)['\"]", config)
    if not version_match:
        raise SystemExit("Config.VERSION não encontrado")
    version = version_match.group(1)

    if f'"{version}"' not in installer:
        raise SystemExit(f"Versão {version} não está declarada no instalador")
    if "VERSION =" not in build or "APP_VERSION" not in build:
        raise SystemExit("Build não possui contrato de versão")
    if "requirements-build.txt" not in build:
        raise SystemExit("Build não instala requirements-build.txt")
    required_python_probes = ("py -3.12", "py -3.11", "python3.12", "python3.11", "Python312", "PY_EXE", "PY_ARGS")
    if any(marker not in build for marker in required_python_probes):
        raise SystemExit("Build não possui descoberta robusta de Python 3.11/3.12")
    required_diagnostics = ("RF_BUILD_LOG", "call :build_main", "type \"%RF_BUILD_LOG%\"")
    if any(marker not in build for marker in required_diagnostics):
        raise SystemExit("Build não preserva diagnóstico quando aberto pelo Explorer")
    required_labels = {
        "build_main", "check_existing_venv", "recreate_venv", "discover_python", "create_venv", "venv_ready",
        "python_not_found", "missing_templates", "missing_static", "missing_routes", "missing_data", "missing_utils", "fail",
    }
    found_labels = set(re.findall(r"(?m)^:([A-Za-z0-9_]+)\s*$", build))
    missing_labels = sorted(required_labels - found_labels)
    if missing_labels:
        raise SystemExit(f"Labels ausentes no BUILD_WINDOWS.bat: {missing_labels}")
    if "--no-browser" not in installer or "--host 0.0.0.0" not in installer:
        raise SystemExit("Tarefa central não está configurada sem navegador e na rede local")
    if "remoteip=localsubnet" not in installer or "profile=private" not in installer:
        raise SystemExit("Firewall não está restrito à rede privada/local")
    if "/api/system/update/health" not in worker:
        raise SystemExit("Health-check do worker está divergente do endpoint real")
    if "--no-browser" not in app or "REGISTROFACIL_OPEN_BROWSER" not in app:
        raise SystemExit("Modo sem navegador não está disponível no executável")
    if not re.search(r"PyInstaller==\d+\.\d+\.\d+", requirements_build):
        raise SystemExit("PyInstaller não está fixado em requirements-build.txt")

    print(f"windows-release-contract: ok ({version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
