from __future__ import annotations

import re
from pathlib import Path

CSS = Path('static/css/color-themes.css').read_text(encoding='utf-8')

def rgb(hex_color: str):
    value = hex_color.lstrip('#')
    return tuple(int(value[i:i+2], 16) / 255 for i in (0, 2, 4))

def linear(channel: float):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

def luminance(hex_color: str):
    r, g, b = rgb(hex_color)
    return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b)

def contrast(foreground: str, background: str):
    first = luminance(foreground)
    second = luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)

print('[report_claim_checks]')
for foreground, background in (('#7A1F2B', '#FFFFFF'), ('#C1663E', '#F3F4F1'), ('#FFFFFF', '#C1663E'), ('#FFFFFF', '#B87A5A'), ('#FFFFFF', '#A85C3A'), ('#7C693C', '#F6F1E6'), ('#A6AFB6', '#101921'), ('#738291', '#2B2B2E'), ('#6B665C', '#F5F2EA')):
    print(f'  {foreground}_on_{background}={contrast(foreground, background):.2f}')

for theme_id, block in re.findall(r'\[data-cor="(paleta-\d+)"\]\s*\{([^}]*)\}', CSS):
    values = dict(re.findall(r'--([\w-]+):\s*(#[0-9A-Fa-f]{6})', block))
    print(f'[{theme_id}]')
    for label, foreground, background in (
        ('primary_on_body', values.get('color-primary'), values.get('background-color-body')),
        ('primary_on_card', values.get('color-primary'), values.get('background-color-card')),
        ('gold_on_body', values.get('gold-primary'), values.get('background-color-body')),
        ('sidebar_text', values.get('sidebar-text'), values.get('sidebar')),
        ('secondary_on_body', values.get('text-color-secondary'), values.get('background-color-body')),
    ):
        if foreground and background:
            print(f'  {label}={foreground}/{background} ratio={contrast(foreground, background):.2f}')
    print('  colors=' + ','.join(f'{key}:{value}' for key, value in values.items() if key in {'color-primary','color-primary-light','color-primary-dark','gold-primary','gold-dark','background-color-body','background-color-card','sidebar','sidebar-hover','sidebar-text'}))
