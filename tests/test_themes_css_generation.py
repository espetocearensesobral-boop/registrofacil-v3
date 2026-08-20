from pathlib import Path

from tools.gerar_themes_css import OUT, render
from tools.verificar_themes import normalizar_css


def test_generated_theme_css_is_synchronized_with_python_catalog():
    actual = Path(OUT).read_text(encoding="utf-8")
    assert normalizar_css(actual) == normalizar_css(render())



def test_theme_identity_colors_are_preserved_while_secondary_foundation_is_cooler():
    from data.themes import PALETAS_INSTITUCIONAIS
    from tools.gerar_themes_css import (
        SECONDARY_BORDER,
        SECONDARY_HOVER,
        SECONDARY_INPUT_BORDER,
        SECONDARY_PAGE_COOL,
        SECONDARY_PAGE_WARM,
    )

    generated = render()
    assert SECONDARY_PAGE_COOL == "#F6F8F9"
    assert SECONDARY_PAGE_WARM == "#F3F6F7"
    assert SECONDARY_HOVER == "#EDF2F4"
    assert SECONDARY_BORDER == "#D2DBE0"
    assert SECONDARY_INPUT_BORDER == "#AEBBC4"

    for palette_id, palette in PALETAS_INSTITUCIONAIS.items():
        start = generated.index(f'[data-cor="{palette_id}"]')
        end = generated.find("\n}", start)
        block = generated[start:end]
        assert f"--rf-palette-color-1: {palette['cores'][0]}" in block
        assert f"--rf-palette-color-2: {palette['cores'][1]}" in block
        assert f"--rf-palette-color-3: {palette['cores'][2]}" in block
        assert f"--rf-palette-color-4: {palette['cores'][3]}" in block
        assert f"--rf-palette-color-5: {palette['cores'][4]}" in block
        assert f"--background-color-hover: {SECONDARY_HOVER}" in block
        assert f"--border-color-default: {SECONDARY_BORDER}" in block
        assert f"--border-color-input: {SECONDARY_INPUT_BORDER}" in block
