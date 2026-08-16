from pathlib import Path

from tools.gerar_themes_css import OUTPUT, render


def test_generated_theme_css_is_synchronized_with_python_catalog():
    assert Path(OUTPUT).read_text(encoding="utf-8") == render()
