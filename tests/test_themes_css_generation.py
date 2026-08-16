from pathlib import Path

from tools.gerar_themes_css import OUT, render
from tools.verificar_themes import normalizar_css


def test_generated_theme_css_is_synchronized_with_python_catalog():
    actual = Path(OUT).read_text(encoding="utf-8")
    assert normalizar_css(actual) == normalizar_css(render())
