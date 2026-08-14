"""Launcher seguro para preparar e ativar releases do RegistroFácil.

O launcher não substitui arquivos diretamente no diretório em execução. Ele
baixa para staging, valida, cria backup e grava um ponteiro de release de forma
atômica. O serviço externo responsável pelo restart pode chamar este módulo.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Any
from urllib.request import Request, urlopen

from config import Config
from data.system_updates import update_state

ProgressCallback = Callable[[str, int, str], None]
_VERSION_RE = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+][0-9A-Za-z.-]+)?$")


@dataclass(frozen=True)
class ReleaseLayout:
    root: Path

    @property
    def downloads(self) -> Path:
        return self.root / "downloads"

    @property
    def staging(self) -> Path:
        return self.root / "staging"

    @property
    def releases(self) -> Path:
        return self.root / "releases"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def current_pointer(self) -> Path:
        return self.root / "current.json"

    def ensure(self) -> None:
        for directory in (self.downloads, self.staging, self.releases, self.backups):
            directory.mkdir(parents=True, exist_ok=True)


def get_release_layout(root: str | os.PathLike[str] | None = None) -> ReleaseLayout:
    configured = root or os.environ.get("REGISTROFACIL_UPDATE_ROOT")
    return ReleaseLayout(Path(configured) if configured else Path(Config.DATA_DIR) / "updates")


def validate_version(version: str) -> str:
    value = str(version or "").strip()
    if not _VERSION_RE.fullmatch(value):
        raise ValueError(f"Versão inválida: {version!r}")
    return value.lstrip("v")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_package(
    url: str,
    destination: Path,
    expected_sha256: str,
    timeout: int = 60,
    progress: ProgressCallback | None = None,
) -> Path:
    if not url.startswith("https://"):
        raise ValueError("O pacote de atualização precisa usar HTTPS.")
    expected = str(expected_sha256 or "").lower().strip()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("SHA-256 esperado inválido.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "RegistroFacil-Updater", "Accept": "application/octet-stream"})
    with urlopen(request, timeout=timeout) as response, destination.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0") or 0)
        downloaded = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            percent = int(downloaded * 100 / total) if total else 0
            if progress:
                progress("downloading", min(percent, 99), f"Baixando pacote ({downloaded} bytes).")

    actual = sha256_file(destination)
    if actual != expected:
        destination.unlink(missing_ok=True)
        raise ValueError(f"SHA-256 divergente: esperado {expected}, obtido {actual}.")
    if progress:
        progress("validating", 100, "Pacote validado com SHA-256.")
    return destination


def _safe_zip_member(member: str, destination: Path) -> Path:
    normalized = Path(member)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError(f"Entrada insegura no pacote: {member}")
    target = (destination / normalized).resolve()
    if target != destination.resolve() and destination.resolve() not in target.parents:
        raise ValueError(f"Entrada fora do staging: {member}")
    return target


def extract_package(package_path: Path, staging_path: Path) -> Path:
    version_dir = staging_path / package_path.stem
    if version_dir.exists():
        shutil.rmtree(version_dir)
    version_dir.mkdir(parents=True, exist_ok=False)

    with zipfile.ZipFile(package_path) as archive:
        for member in archive.infolist():
            target = _safe_zip_member(member.filename, version_dir)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as destination:
                shutil.copyfileobj(source, destination)
    return version_dir


def backup_installation(
    layout: ReleaseLayout,
    db_path: str | os.PathLike[str],
    upload_root: str | os.PathLike[str] | None = None,
    key_files: tuple[str | os.PathLike[str], ...] = (),
) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = layout.backups / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)

    db_source = Path(db_path)
    if db_source.is_file():
        shutil.copy2(db_source, backup_dir / db_source.name)
    if upload_root and Path(upload_root).is_dir():
        shutil.copytree(upload_root, backup_dir / "uploads", dirs_exist_ok=True)
    keys_dir = backup_dir / "keys"
    for key_file in key_files:
        source = Path(key_file)
        if source.is_file():
            keys_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, keys_dir / source.name)
    return backup_dir


def activate_release(layout: ReleaseLayout, version: str) -> Path:
    normalized = validate_version(version)
    release_dir = layout.releases / normalized
    if not release_dir.is_dir():
        raise FileNotFoundError(f"Release não preparada: {normalized}")
    layout.current_pointer.parent.mkdir(parents=True, exist_ok=True)
    temporary = layout.current_pointer.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({"version": normalized, "path": str(release_dir)}, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(temporary, layout.current_pointer)
    return release_dir


def prepare_release(
    manifest: dict[str, Any],
    layout: ReleaseLayout | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    layout = layout or get_release_layout()
    layout.ensure()
    version = validate_version(manifest.get("version"))
    package_url = str(manifest.get("package_url", ""))
    package_hash = str(manifest.get("sha256", ""))
    if progress:
        progress("preparing", 1, f"Preparando a versão {version}.")

    package_path = layout.downloads / f"RegistroFacil-{version}.zip"
    download_package(package_url, package_path, package_hash, progress=progress)
    if progress:
        progress("backing_up", 0, "Pacote validado; aguardando backup antes da ativação.")
    staging_path = extract_package(package_path, layout.staging)
    release_dir = layout.releases / version
    if release_dir.exists():
        shutil.rmtree(release_dir)
    shutil.move(str(staging_path), str(release_dir))
    (release_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if progress:
        progress("ready", 100, f"Release {version} preparada; pronta para ativação.")
    return release_dir


def run_progress_state(state: str, progress: int, message: str, **extra: Any) -> None:
    update_state(state=state, progress=progress, message=message, **extra)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Launcher seguro do RegistroFácil")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Baixa, valida e prepara uma release")
    prepare.add_argument("manifest", type=Path, help="Caminho do manifesto JSON")
    prepare.add_argument("--root", type=Path, default=None)

    backup = subparsers.add_parser("backup", help="Cria backup da instalação")
    backup.add_argument("--root", type=Path, default=None)
    backup.add_argument("--database", type=Path, default=Path(Config.DATABASE_PATH))
    backup.add_argument("--uploads", type=Path, default=Path(Config.UPLOAD_ROOT_DIR))

    activate = subparsers.add_parser("activate", help="Ativa uma release já preparada")
    activate.add_argument("version")
    activate.add_argument("--root", type=Path, default=None)

    args = parser.parse_args(argv)
    layout = ReleaseLayout(args.root) if getattr(args, "root", None) else get_release_layout()
    layout.ensure()

    if args.command == "prepare":
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        prepare_release(manifest, layout, progress=run_progress_state)
        return 0
    if args.command == "backup":
        backup_installation(
            layout,
            args.database,
            args.uploads,
            (Path(Config.DATA_DIR) / ".secret_key", Path(Config.DATA_DIR) / ".encryption_key"),
        )
        return 0
    if args.command == "activate":
        activate_release(layout, args.version)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
