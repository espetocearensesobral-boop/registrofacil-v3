#!/usr/bin/env python3
"""Verifica se color-themes.css está sincronizado com data/themes.py.
Uso no CI: python tools/verificar_themes.py || exit 1
"""
import os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, "static", "css", "color-themes.css")

# Backup do atual
with open(CSS, encoding="utf-8") as f:
    original = f.read()

# Regenera
sys.path.insert(0, ROOT)
from tools.gerar_themes_css import main as gerar
gerar()

with open(CSS, encoding="utf-8") as f:
    gerado = f.read()

# Restaura original
with open(CSS, "w", encoding="utf-8") as f:
    f.write(original)

if original == gerado:
    print("✅ color-themes.css sincronizado com data/themes.py")
    sys.exit(0)
else:
    print("❌ color-themes.css DIVERGE de data/themes.py")
    print("   Rode: python tools/gerar_themes_css.py")
    sys.exit(1)