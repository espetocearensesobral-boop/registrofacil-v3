"""Catálogo das aparências institucionais definidas no guia visual."""

from __future__ import annotations

from copy import deepcopy


APPEARANCE_DEFAULT = "paleta-01"

SIDEBAR_SELECTION_COLORS = {
    "grafite-vinho": {"id": "grafite-vinho", "nome": "Vinho institucional", "hex": "#7A1F2B"},
    "dourado": {"id": "dourado", "nome": "Dourado", "hex": "#8B6F47"},
    "azul-marinho": {"id": "azul-marinho", "nome": "Azul-marinho", "hex": "#1B3A5C"},
    "vinho": {"id": "vinho", "nome": "Vinho jurídico", "hex": "#6B1F2E"},
    "verde-esmeralda": {"id": "verde-esmeralda", "nome": "Verde esmeralda", "hex": "#1B5E20"},
    "azul-petroleo": {"id": "azul-petroleo", "nome": "Azul petróleo", "hex": "#006064"},
    "roxo-real": {"id": "roxo-real", "nome": "Roxo real", "hex": "#4A148C"},
    "azul-royal": {"id": "azul-royal", "nome": "Azul royal", "hex": "#1A237E"},
    "verde-oliva": {"id": "verde-oliva", "nome": "Verde oliva", "hex": "#556B2F"},
    "terracota": {"id": "terracota", "nome": "Terracota", "hex": "#8B4513"},
    "azul-cobalto": {"id": "azul-cobalto", "nome": "Azul cobalto", "hex": "#1565C0"},
    "magenta": {"id": "magenta", "nome": "Magenta sóbrio", "hex": "#880E4F"},
    "cinza-grafite": {"id": "cinza-grafite", "nome": "Cinza grafite", "hex": "#37474F"},
    "teal": {"id": "teal", "nome": "Teal institucional", "hex": "#00695C"},
    "indigo": {"id": "indigo", "nome": "Índigo profundo", "hex": "#283593"},
    "ambar": {"id": "ambar", "nome": "Âmbar escuro", "hex": "#B45309"},
    "verde-floresta": {"id": "verde-floresta", "nome": "Verde floresta", "hex": "#1B4332"},
    "azul-aco": {"id": "azul-aco", "nome": "Azul aço", "hex": "#2C5F7C"},
    "coral": {"id": "coral", "nome": "Coral terroso", "hex": "#A0522D"},
    "lavanda": {"id": "lavanda", "nome": "Lavanda escura", "hex": "#5D4E8C"},
    "preto-classico": {"id": "preto-classico", "nome": "Preto clássico", "hex": "#1A1A1A"},
    "vermelho-rubi": {"id": "vermelho-rubi", "nome": "Vermelho rubi", "hex": "#991B1B"},
    "rosa-antigo": {"id": "rosa-antigo", "nome": "Rosa antigo", "hex": "#9D174D"},
    "laranja-queimado": {"id": "laranja-queimado", "nome": "Laranja queimado", "hex": "#9A3412"},
    "verde-jade": {"id": "verde-jade", "nome": "Verde jade", "hex": "#065F46"},
    "azul-meia-noite": {"id": "azul-meia-noite", "nome": "Azul meia-noite", "hex": "#0F172A"},
    "violeta-ametista": {"id": "violeta-ametista", "nome": "Violeta ametista", "hex": "#4C1D95"},
    "marrom-cafe": {"id": "marrom-cafe", "nome": "Marrom café", "hex": "#451A03"},
    "cinza-carvao": {"id": "cinza-carvao", "nome": "Cinza carvão", "hex": "#1F2937"},
    "verde-salvia": {"id": "verde-salvia", "nome": "Verde sálvia", "hex": "#3F6212"},
    "azul-oceano": {"id": "azul-oceano", "nome": "Azul oceano", "hex": "#075985"},
}

PALETAS_INSTITUCIONAIS = {
    "paleta-01": {
        "id": "paleta-01",
        "numero": "01",
        "nome": "Confiança Institucional",
        "descricao": "Azul-marinho profundo com dourado envelhecido, inspirado em selos, carimbos e livros de registro.",
        "primary": "#0F2A43",
        "primary_light": "#1B4368",
        "primary_dark": "#0A1E30",
        "accent": "#B08D3E",
        "background": "#F5F2EA",
        "paper": "#FFFFFF",
        "text": "#1D1B18",
        "muted": "#6B665C",
        "line": "#D9D2C2",
        "success_bg": "#E4F1E9",
        "success_text": "#1E5C3E",
        "danger_bg": "#FDECEC",
        "danger_text": "#8C2A2A",
        "warning_bg": "#FCF3DC",
        "warning_text": "#7A5A0A",
        "info_bg": "#E7EEF5",
        "info_text": "#26476B",
    },
    "paleta-02": {
        "id": "paleta-02",
        "numero": "02",
        "nome": "Verde Cartorial Contemporâneo",
        "descricao": "Verde-escuro institucional com terracota suave, equilibrando tradição e uma leitura digital confiável.",
        "primary": "#123C31",
        "primary_light": "#1E5C4A",
        "primary_dark": "#0A251E",
        "accent": "#C1663E",
        "background": "#F3F4F1",
        "paper": "#FFFFFF",
        "text": "#20261F",
        "muted": "#687168",
        "line": "#D6DAD2",
        "success_bg": "#E3F0E9",
        "success_text": "#155C42",
        "danger_bg": "#FBEAE3",
        "danger_text": "#9C4322",
        "warning_bg": "#FCF3DC",
        "warning_text": "#7A5A0A",
        "info_bg": "#E9F0EC",
        "info_text": "#1E4A3A",
    },
    "paleta-03": {
        "id": "paleta-03",
        "numero": "03",
        "nome": "Grafite & Vinho — Minimalista",
        "descricao": "Grafite neutro com vinho/bordô como cor de autoridade, priorizando densidade de informação e foco.",
        "primary": "#2B2B2E",
        "primary_light": "#45454A",
        "primary_dark": "#18181A",
        "accent": "#7A1F2B",
        "background": "#F5F5F4",
        "paper": "#FFFFFF",
        "text": "#1A1A1B",
        "muted": "#6B665C",
        "line": "#DEDEDC",
        "success_bg": "#E9EFE9",
        "success_text": "#2C5C36",
        "danger_bg": "#F6E7E9",
        "danger_text": "#7A1F2B",
        "warning_bg": "#F3EEDD",
        "warning_text": "#6E5A16",
        "info_bg": "#ECECEB",
        "info_text": "#3A3A3C",
    },
}


def listar_paletas_institucionais() -> list[dict]:
    """Retorna cópias seguras do catálogo para renderização nos templates."""
    return [deepcopy(paleta) for paleta in PALETAS_INSTITUCIONAIS.values()]


def tema_institucional_valido(tema: str | None) -> bool:
    return bool(tema and tema in PALETAS_INSTITUCIONAIS)


def listar_cores_sidebar() -> list[dict]:
    return [deepcopy(cor) for cor in SIDEBAR_SELECTION_COLORS.values()]


def cor_sidebar_valida(cor: str | None) -> bool:
    return bool(cor and cor in {item['hex'] for item in SIDEBAR_SELECTION_COLORS.values()})


def obter_cor_sidebar(cor: str | None) -> str:
    if cor_sidebar_valida(cor):
        return cor
    return SIDEBAR_SELECTION_COLORS['azul-marinho']['hex']


def obter_paleta_institucional(tema: str | None) -> dict:
    return deepcopy(PALETAS_INSTITUCIONAIS.get(tema or APPEARANCE_DEFAULT, PALETAS_INSTITUCIONAIS[APPEARANCE_DEFAULT]))
