"""Gera static/css/color-themes.css a partir do catálogo Python."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data.themes import APPEARANCE_DEFAULT, PALETAS_INSTITUCIONAIS  # noqa: E402

OUTPUT = ROOT / "static" / "css" / "color-themes.css"


def rgba(hex_color: str, alpha: float) -> str:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return f"rgba({red}, {green}, {blue}, {alpha:.2f})"


def theme_block(theme_id: str, palette: dict) -> str:
    primary = palette["primary"]
    accent = palette["accent"]
    background = palette["background"]
    paper = palette["paper"]
    line = palette["line"]
    danger = palette["danger_text"]
    warning = palette["warning_text"]
    info = palette["info_text"]
    return f'''/* ============================================================
   {palette["numero"]} · {palette["nome"]}
   ============================================================ */
[data-cor="{theme_id}"] {{
    --color-primary: {primary};
    --color-primary-light: {palette["primary_light"]};
    --color-primary-dark: {palette["primary_dark"]};
    --color-primary-subtle: {rgba(primary, 0.12)};
    --color-primary-rgb: {int(primary[1:3], 16)}, {int(primary[3:5], 16)}, {int(primary[5:7], 16)};
    --color-gold-primary: {accent};
    --color-gold-dark: color-mix(in srgb, {accent} 78%, #000000);

    --background-color-body: {background};
    --background-color-card: {paper};
    --background-color-header: {paper};
    --background-color-hover: color-mix(in srgb, {background} 90%, {primary});
    --background-color-input-bg: {paper};

    --sidebar: {palette["sidebar"]};
    --sidebar-hover: {palette["sidebar_hover"]};
    --sidebar-text: {palette["sidebar_text"]};
    --sidebar-active-text: {palette["sidebar_active_text"]};

    --text-color-primary: {palette["text"]};
    --text-color-secondary: {palette["muted"]};
    --text-color-link: {primary};
    --border-color-default: {line};
    --border-color-input: color-mix(in srgb, {line} 78%, {primary});
    --border-color-dark: {palette["primary_dark"]};

    --color-success: {palette["success_text"]};
    --color-error: {danger};
    --color-warning: {warning};
    --color-info: {info};
    --danger-bg: color-mix(in srgb, {danger} 10%, {paper});
    --danger-text: {danger};
    --warning-bg: color-mix(in srgb, {warning} 12%, {paper});
    --warning-text: {warning};
    --info-bg: color-mix(in srgb, {info} 10%, {paper});
    --info-text: {info};
}}
'''


SEMANTIC_BLOCK = '''/* ─────────────────────────────────────────────────────────────
   BLOCO SEMÂNTICO COMPARTILHADO (aplicado a qualquer tema)
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

    --rf-text-primary: var(--text-color-primary);
    --rf-text-secondary: var(--text-color-secondary);
    --rf-text-muted: var(--text-color-secondary);
    --rf-text-strong: var(--text-color-primary);
    --rf-text-body: var(--text-color-primary);
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

    /* Aliases de compatibilidade para folhas estruturais legadas. */
    --font-xs: var(--rf-font-xs);
    --font-sm: var(--rf-font-sm);
    --font-base: var(--rf-font-base);
    --font-lg: var(--rf-font-lg);
    --font-xl: var(--rf-font-xl);
    --color-gray-light: var(--background-color-hover);
    --color-gray-medium: var(--border-color-input);
    --sidebar-header-height: 4.25rem;
}
'''


def render() -> str:
    default = PALETAS_INSTITUCIONAIS[APPEARANCE_DEFAULT]
    content = [
        "/* ============================================================",
        "   COLOR-THEMES.CSS — Registro Fácil v3.25",
        "   Gerado por tools/gerar_themes_css.py a partir de data/themes.py.",
        "   NÃO editar manualmente — execute o gerador após alterar o catálogo.",
        "   ============================================================ */\n",
        "/* Fallback :root — tema padrão: Olivar & Cobre */",
        ":root {",
        f"    --color-primary: {default['primary']};",
        f"    --color-primary-light: {default['primary_light']};",
        f"    --color-primary-dark: {default['primary_dark']};",
        f"    --color-primary-subtle: {rgba(default['primary'], 0.12)};",
        f"    --color-primary-rgb: {int(default['primary'][1:3], 16)}, {int(default['primary'][3:5], 16)}, {int(default['primary'][5:7], 16)};",
        "    --color-primary-contrast: #FFFFFF;",
        f"    --color-gold-primary: {default['accent']};",
        f"    --color-gold-dark: color-mix(in srgb, {default['accent']} 78%, #000000);",
        f"    --background-color-body: {default['background']};",
        f"    --background-color-card: {default['paper']};",
        f"    --background-color-header: {default['paper']};",
        f"    --background-color-hover: color-mix(in srgb, {default['background']} 90%, {default['primary']});",
        f"    --background-color-input-bg: {default['paper']};",
        f"    --text-color-primary: {default['text']};",
        f"    --text-color-secondary: {default['muted']};",
        f"    --text-color-link: {default['primary']};",
        f"    --border-color-default: {default['line']};",
        f"    --border-color-input: color-mix(in srgb, {default['line']} 78%, {default['primary']});",
        f"    --border-color-dark: {default['primary_dark']};",
        f"    --sidebar: {default['sidebar']};",
        f"    --sidebar-hover: {default['sidebar_hover']};",
        f"    --sidebar-text: {default['sidebar_text']};",
        f"    --sidebar-active-text: {default['sidebar_active_text']};",
        f"    --color-success: {default['success_text']};",
        f"    --color-error: {default['danger_text']};",
        f"    --color-warning: {default['warning_text']};",
        f"    --color-info: {default['info_text']};",
        "    --rf-action-tertiary: var(--color-gold-primary);",
        "    --rf-action-tertiary-hover: var(--color-gold-dark);",
        "    --font-xs: .75rem; --font-sm: .875rem; --font-base: 1rem; --font-lg: 1.125rem; --font-xl: 1.375rem;",
        "    --color-gray-light: var(--background-color-hover); --color-gray-medium: var(--border-color-input);",
        "    --sidebar-header-height: 4.25rem; --rf-sidebar-collapsed-width: 4rem;",
        "}\n",
        SEMANTIC_BLOCK,
    ]
    content.extend(theme_block(theme_id, palette) for theme_id, palette in PALETAS_INSTITUCIONAIS.items())
    return "\n".join(content).rstrip() + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"generated {len(PALETAS_INSTITUCIONAIS)} themes -> {OUTPUT}")
