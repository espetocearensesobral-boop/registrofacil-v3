#!/usr/bin/env python3
"""
Gera static/css/color-themes.css a partir de data/themes.py.
Single source of truth — o CSS nunca mais fica desatualizado.

Uso:
    python tools/gerar_themes_css.py

No CI (falha se divergir):
    cp static/css/color-themes.css /tmp/themes_original.css
    python tools/gerar_themes_css.py
    diff -q static/css/color-themes.css /tmp/themes_original.css
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.themes import PALETAS_INSTITUCIONAIS, APPEARANCE_DEFAULT

OUT = os.path.join(ROOT, "static", "css", "color-themes.css")


def rgba(h: str, a: float) -> str:
    h = h.lstrip("#")
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {a})"


def rgb3(h: str) -> str:
    h = h.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))


# ── Bloco semântico compartilhado (constante — tokens de componentes) ──
SEMANTICO = """
/* ─────────────────────────────────────────────────────────────
   BLOCO SEMÂNTICO COMPARTILHADO
   Mapeia variáveis primitivas de cada tema para os tokens
   semânticos usados por componentes (sidebar, botões, badges, etc.)
   ───────────────────────────────────────────────────────────── */
[data-cor^="paleta-"] {
    --text-color-light: var(--sidebar-text);
    --background-color-sidebar: var(--sidebar);
    --background-color-sidebar-hover: var(--sidebar-hover);
    --color-primary-contrast: #FFFFFF;

    --rf-theme-accent: var(--color-gold-primary);
    --rf-theme-accent-dark: var(--color-gold-dark);
    --rf-theme-danger-bg: var(--danger-bg);
    --rf-theme-danger-text: var(--danger-text);
    --rf-theme-warning-bg: var(--warning-bg);
    --rf-theme-warning-text: var(--warning-text);
    --rf-theme-info-bg: var(--info-bg);
    --rf-theme-info-text: var(--info-text);

    /* Fundação cromática neutra: a identidade fica nos elementos de ação. */
    --rf-text-heading: #121212;
    --rf-text-primary: #121212;
    --rf-text-secondary: #2A2A2A;
    --rf-text-muted: #2A2A2A;
    --rf-text-strong: #121212;
    --rf-text-body: #2A2A2A;

    --rf-bg-cold: #F8F8F8;
    --rf-bg-warm: #FDF8F0;
    --rf-surface-modal: #FFFFFF;
    --rf-text-on-primary: var(--color-primary-contrast, #FFFFFF);
    --rf-text-on-sidebar: var(--sidebar-text);
    --rf-text-link: var(--text-color-link);

    --rf-surface-body: var(--background-color-body);
    --rf-surface-card: var(--background-color-card);
    --rf-surface-muted: var(--background-color-hover);
    --rf-surface-input: var(--background-color-input-bg);
    --rf-surface-hover: var(--background-color-hover);
    --rf-surface-overlay: color-mix(in srgb, var(--background-color-body) 88%, #000000);
    --rf-surface: var(--background-color-card);
    --rf-page: var(--background-color-body);
    --rf-surface-modal: #FFFFFF;

    --rf-border: var(--border-color-default);
    --rf-border-subtle: color-mix(in srgb, var(--border-color-default) 60%, transparent);
    --rf-border-input: var(--border-color-input);
    --rf-border-strong: var(--border-color-dark);

    --rf-action-primary: var(--color-primary);
    --rf-action-primary-hover: var(--color-primary-light);
    --rf-action-primary-active: var(--color-primary-dark);
    --rf-action-secondary: var(--background-color-card);
    --rf-action-secondary-hover: var(--background-color-hover);
    --rf-action-tertiary: var(--color-gold-primary);
    --rf-action-tertiary-hover: var(--color-gold-dark);

    --rf-accent: var(--color-gold-primary);
    --rf-accent-hover: var(--color-gold-dark);
    --rf-accent-subtle: var(--color-primary-subtle);

    --rf-danger: var(--color-error);
    --rf-danger-hover: color-mix(in srgb, var(--color-error) 82%, #000000);
    --rf-danger-surface: var(--danger-bg);
    --rf-danger-text: var(--danger-text);

    --rf-success: var(--color-success);
    --rf-success-hover: color-mix(in srgb, var(--color-success) 82%, #000000);
    --rf-success-surface: color-mix(in srgb, var(--color-success) 12%, var(--background-color-card));
    --rf-success-text: var(--color-success);

    --rf-warning: var(--color-warning);
    --rf-warning-hover: color-mix(in srgb, var(--color-warning) 82%, #000000);
    --rf-warning-surface: var(--warning-bg);
    --rf-warning-text: var(--warning-text);

    --rf-info: var(--color-info);
    --rf-info-hover: color-mix(in srgb, var(--color-info) 82%, #000000);
    --rf-info-surface: var(--info-bg);
    --rf-info-text: var(--info-text);

    --rf-sidebar-surface: var(--sidebar);
    --rf-sidebar-hover: var(--sidebar-hover);
    --rf-sidebar-active: var(--color-gold-primary);
    --rf-sidebar-text: var(--sidebar-text);
    --rf-sidebar-active-text: var(--sidebar-active-text);
    --rf-sidebar-border: var(--border-color-dark);

    --rf-font-sans: "Source Sans 3", sans-serif;
    --rf-font-display: "Fraunces", Georgia, serif;
    --rf-font-mono: "IBM Plex Mono", monospace;

    --rf-font-xs: .75rem;
    --rf-font-sm: .875rem;
    --rf-font-base: 1rem;
    --rf-font-lg: 1.125rem;
    --rf-font-xl: 1.375rem;

    --rf-control-height: 2.75rem;
    --rf-sidebar-width: 15rem;
}
"""


WARM_FAMILIES = {
    'vinho', 'café', 'ferrugem', 'cobre', 'ameixa', 'rosa-queimado', 'argila'
}


def foundations(p: dict) -> tuple[str, str]:
    """Retorna fundo de página e superfície limpa para a família do tema."""
    page = '#FDF8F0' if p['familia'] in WARM_FAMILIES else '#F8F8F8'
    return page, '#FFFFFF'


def render_fallback(p: dict) -> str:
    page, surface = foundations(p)
    return f"""
/* ─────────────────────────────────────────────────────────────
   FALLBACK :root (tema padrão: {p['nome']})
   ───────────────────────────────────────────────────────────── */
:root {{
    --color-primary: {p['primary']};
    --color-primary-light: {p['primary_light']};
    --color-primary-dark: {p['primary_dark']};
    --color-primary-subtle: {rgba(p['primary'], .12)};
    --color-primary-rgb: {rgb3(p['primary'])};
    --color-primary-contrast: #FFFFFF;
    --rf-palette-color-1: {p['cores'][0]};
    --rf-palette-color-2: {p['cores'][1]};
    --rf-palette-color-3: {p['cores'][2]};
    --rf-palette-color-4: {p['cores'][3]};
    --rf-palette-color-5: {p['cores'][4]};

    --color-gold-primary: {p['accent']};
    --color-gold-dark: color-mix(in srgb, {p['accent']} 72%, #000);

    --rf-action-tertiary: {p['accent']};
    --rf-action-tertiary-hover: color-mix(in srgb, {p['accent']} 72%, #000);

    --background-color-body: {page};
    --background-color-card: {surface};
    --background-color-header: {surface};
    --background-color-hover: color-mix(in srgb, {page} 90%, {p['primary']});
    --background-color-input-bg: {surface};

    --text-color-primary: #121212;
    --text-color-secondary: #2A2A2A;
    --text-color-link: {p['primary']};

    --border-color-default: {p['line']};
    --border-color-input: color-mix(in srgb, {p['line']} 78%, {p['primary']});
    --border-color-dark: {p['primary_dark']};

    --sidebar: {p['sidebar']};
    --sidebar-hover: {p['sidebar_hover']};
    --sidebar-text: {p['sidebar_text']};
    --sidebar-active-text: {p['sidebar_active_text']};

    --color-success: {p['success_text']};
    --color-error: {p['danger_text']};
    --color-warning: {p['warning_text']};
    --color-info: {p['info_text']};
    --danger-bg: color-mix(in srgb, {p['danger_text']} 10%, {surface});
    --danger-text: {p['danger_text']};
    --warning-bg: color-mix(in srgb, {p['warning_text']} 12%, {surface});
    --warning-text: {p['warning_text']};
    --info-bg: color-mix(in srgb, {p['info_text']} 10%, {surface});
    --info-text: {p['info_text']};
}}
"""


def render_paleta(pid: str, p: dict) -> str:
    page, surface = foundations(p)
    return f"""
/* ============================================================
   {p['numero']} · {p['nome']} — {p['descricao']}
   ============================================================ */
[data-cor="{pid}"] {{
    --color-primary: {p['primary']}; --color-primary-light: {p['primary_light']}; --color-primary-dark: {p['primary_dark']};
    --color-primary-subtle: {rgba(p['primary'], .12)}; --color-primary-rgb: {rgb3(p['primary'])};
    --rf-palette-color-1: {p['cores'][0]}; --rf-palette-color-2: {p['cores'][1]}; --rf-palette-color-3: {p['cores'][2]};
    --rf-palette-color-4: {p['cores'][3]}; --rf-palette-color-5: {p['cores'][4]};
    --color-gold-primary: {p['accent']}; --color-gold-dark: color-mix(in srgb, {p['accent']} 72%, #000);
    --background-color-body: {page}; --background-color-card: {surface}; --background-color-header: {surface};
    --background-color-hover: color-mix(in srgb, {page} 90%, {p['primary']}); --background-color-input-bg: {surface};
    --sidebar: {p['sidebar']}; --sidebar-hover: {p['sidebar_hover']}; --sidebar-text: {p['sidebar_text']}; --sidebar-active-text: {p['sidebar_active_text']};
    --text-color-primary: #121212; --text-color-secondary: #2A2A2A; --text-color-link: {p['primary']};
    --border-color-default: {p['line']}; --border-color-input: color-mix(in srgb, {p['line']} 78%, {p['primary']}); --border-color-dark: {p['primary_dark']};
    --color-success: {p['success_text']}; --color-error: {p['danger_text']}; --color-warning: {p['warning_text']}; --color-info: {p['info_text']};
    --danger-bg: color-mix(in srgb, {p['danger_text']} 10%, {surface}); --danger-text: {p['danger_text']};
    --warning-bg: color-mix(in srgb, {p['warning_text']} 12%, {surface}); --warning-text: {p['warning_text']};
    --info-bg: color-mix(in srgb, {p['info_text']} 10%, {surface}); --info-text: {p['info_text']};
}}
"""


def render() -> str:
    header = (
        "/* ============================================================\n"
        "   COLOR-THEMES.CSS — Registro Fácil v3.25\n"
        "   Gerado por tools/gerar_themes_css.py — NÃO editar manualmente.\n"
        f"   {len(PALETAS_INSTITUCIONAIS)} paletas institucionais · "
        "single source of truth em data/themes.py\n"
        "   ============================================================ */\n"
    )

    fallback = PALETAS_INSTITUCIONAIS[APPEARANCE_DEFAULT]
    blocos = [header, render_fallback(fallback), SEMANTICO]
    for pid, p in PALETAS_INSTITUCIONAIS.items():
        blocos.append(render_paleta(pid, p))
    return "\n".join(blocos)

def main() -> int:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render())
    print(f"✅ {len(PALETAS_INSTITUCIONAIS)} paletas → {OUT}")
    return 0

if __name__ == "__main__":
    sys.exit(main())