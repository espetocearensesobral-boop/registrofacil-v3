"""Configuração externa do canal de atualização.

O arquivo fica fora do código empacotado, em DATA_DIR, para que o endereço do
manifesto possa ser corrigido sem gerar uma nova versão do aplicativo.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from typing import Any

from config import Config, DATA_DIR

DEFAULT_MANIFEST_URL = (
    "https://github.com/espetocearensesobral-boop/registrofacil-v3/"
    "releases/latest/download/manifest.json"
)
DEFAULT_FALLBACK_MANIFEST_URL = (
    "https://raw.githubusercontent.com/espetocearensesobral-boop/registrofacil-v3/"
    "main/updates/manifest.json"
)
DEFAULT_UPDATE_CONFIG_PATH = Path(DATA_DIR) / "update.ini"


def load_update_settings(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Carrega o INI externo e aplica variáveis de ambiente como override."""
    config_path = Path(path or os.environ.get("REGISTROFACIL_UPDATE_CONFIG", DEFAULT_UPDATE_CONFIG_PATH))
    parser = configparser.ConfigParser()
    if config_path.is_file():
        parser.read(config_path, encoding="utf-8")

    section = parser["update"] if parser.has_section("update") else {}
    primary = os.environ.get(
        "REGISTROFACIL_UPDATE_MANIFEST_URL",
        section.get("manifest_url", DEFAULT_MANIFEST_URL),
    ).strip()
    fallback = os.environ.get(
        "REGISTROFACIL_UPDATE_FALLBACK_URL",
        section.get("fallback_manifest_url", DEFAULT_FALLBACK_MANIFEST_URL),
    ).strip()
    channel = os.environ.get("REGISTROFACIL_UPDATE_CHANNEL", section.get("channel", "stable")).strip()

    try:
        timeout = int(os.environ.get("REGISTROFACIL_UPDATE_TIMEOUT", section.get("timeout_seconds", "20")))
    except (TypeError, ValueError):
        timeout = 20

    return {
        "config_path": str(config_path),
        "manifest_url": primary,
        "fallback_manifest_url": fallback,
        "channel": channel or "stable",
        "timeout_seconds": max(5, min(timeout, 120)),
    }


def manifest_urls(settings: dict[str, Any] | None = None) -> list[str]:
    settings = settings or load_update_settings()
    urls = [settings.get("manifest_url"), settings.get("fallback_manifest_url")]
    return list(dict.fromkeys(url for url in urls if url and url.startswith("https://")))
