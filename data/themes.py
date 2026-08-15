"""Catálogo das aparências institucionais definidas no guia visual."""

from __future__ import annotations

from copy import deepcopy


APPEARANCE_DEFAULT_KEY = "appearance_default_theme"
APPEARANCE_DEFAULT = "paleta-03"

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


def obter_paleta_institucional(tema: str | None) -> dict:
    return deepcopy(PALETAS_INSTITUCIONAIS.get(tema or APPEARANCE_DEFAULT, PALETAS_INSTITUCIONAIS[APPEARANCE_DEFAULT]))
