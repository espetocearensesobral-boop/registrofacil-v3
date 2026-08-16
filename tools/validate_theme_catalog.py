from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.themes import APPEARANCE_DEFAULT, PALETAS_INSTITUCIONAIS  # noqa: E402


def rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip('#')
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    red, green, blue = rgb(hex_color)
    return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)


def contrast(foreground: str, background: str) -> float:
    first, second = luminance(foreground), luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


require(APPEARANCE_DEFAULT == 'paleta-01', 'default theme must be paleta-01')
require(len(PALETAS_INSTITUCIONAIS) == 20, 'catalog must contain exactly 20 themes')
require(len({theme['familia'] for theme in PALETAS_INSTITUCIONAIS.values()}) == 20, 'theme families must be unique')
warm_families = {'vinho', 'café', 'ferrugem', 'cobre', 'ameixa', 'rosa-queimado', 'argila'}

for theme_id, theme in PALETAS_INSTITUCIONAIS.items():
    colors = theme['cores']
    require(len(colors) == 5, f'{theme_id}: palette must contain exactly five colors')
    require(len(set(colors)) == 5, f'{theme_id}: palette colors must be distinct')
    require(all(isinstance(color, str) and len(color) == 7 and color.startswith('#') for color in colors), f'{theme_id}: invalid hex color')
    expected_background = '#FDF8F0' if theme['familia'] in warm_families else '#F8F8F8'
    require(theme['background'] == expected_background, f'{theme_id}: foundation background does not match family')
    require(theme['paper'] == '#FFFFFF', f'{theme_id}: modal/card surface must be white')
    require(colors[3] == expected_background and colors[4] == '#FFFFFF', f'{theme_id}: palette foundation colors are inconsistent')
    require(theme['text'] == '#121212', f'{theme_id}: heading text must use premium black')
    require(theme['muted'] == '#2A2A2A', f'{theme_id}: body text must use deep neutral')
    require(contrast(theme['text'], theme['background']) >= 4.5, f'{theme_id}: text/background contrast below 4.5')
    require(contrast(theme['text'], theme['paper']) >= 4.5, f'{theme_id}: text/paper contrast below 4.5')
    require(contrast(theme['sidebar_text'], theme['sidebar']) >= 4.5, f'{theme_id}: sidebar text contrast below 4.5')
    require(contrast('#FFFFFF', theme['primary']) >= 4.5, f'{theme_id}: primary button contrast below 4.5')
    require(contrast('#FFFFFF', theme['accent']) >= 4.5, f'{theme_id}: tertiary action contrast below 4.5')

first = PALETAS_INSTITUCIONAIS['paleta-01']
require(first['cores'] == ['#111315', '#2B3035', '#7D6A4B', '#F8F8F8', '#FFFFFF'], 'default palette is not the approved matte black palette')
require(first['sidebar'] == '#111315', 'default sidebar is not matte black')

print('theme-catalog-validation: ok; themes=20; colors_per_theme=5; families=20; default=matte-black')
