#!/usr/bin/env python3
"""Verifica se color-themes.css está sincronizado semanticamente com data/themes.py."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "static" / "css" / "color-themes.css"
sys.path.insert(0, str(ROOT))

from tools.gerar_themes_css import render  # noqa: E402


def normalizar_css(texto: str) -> str:
    """Remove comentários e diferenças de whitespace sem alterar valores CSS."""
    sem_comentarios = re.sub(r"/\*.*?\*/", "", texto, flags=re.DOTALL)
    return re.sub(r"\s+", "", sem_comentarios)


def main() -> int:
    original = CSS.read_text(encoding="utf-8")
    gerado = render()

    if normalizar_css(original) == normalizar_css(gerado):
        print("color-themes.css sincronizado semanticamente com data/themes.py")
        return 0

    print("color-themes.css diverge semanticamente de data/themes.py")
    print("Rode: python tools/gerar_themes_css.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
