"""Catálogo das seis aparências institucionais completas do Registro Fácil."""

from __future__ import annotations

from copy import deepcopy


APPEARANCE_DEFAULT = "paleta-01"

PALETAS_INSTITUCIONAIS = {
    "paleta-01": {
        "id": "paleta-01", "numero": "01", "nome": "Confiança Institucional",
        "descricao": "Azul-marinho profundo com dourado envelhecido, inspirado em selos e livros de registro.",
        "primary": "#0F2A43", "primary_light": "#1B4368", "primary_dark": "#0A1E30", "accent": "#B08D3E",
        "background": "#F5F2EA", "paper": "#FFFFFF", "text": "#1D1B18", "muted": "#6B665C", "line": "#D9D2C2",
        "success_bg": "#E4F1E9", "success_text": "#1E5C3E", "danger_bg": "#FDECEC", "danger_text": "#8C2A2A",
        "warning_bg": "#FCF3DC", "warning_text": "#7A5A0A", "info_bg": "#E7EEF5", "info_text": "#26476B",
        "sidebar": "#0F2A43", "sidebar_hover": "#1B4368", "sidebar_text": "#FFFFFF", "sidebar_active_text": "#FFFFFF",
    },
    "paleta-02": {
        "id": "paleta-02", "numero": "02", "nome": "Verde Cartorial Contemporâneo",
        "descricao": "Verde-escuro institucional com terracota suave, equilibrando tradição e leitura digital.",
        "primary": "#123C31", "primary_light": "#1E5C4A", "primary_dark": "#0A251E", "accent": "#C1663E",
        "background": "#F3F4F1", "paper": "#FFFFFF", "text": "#20261F", "muted": "#687168", "line": "#D6DAD2",
        "success_bg": "#E3F0E9", "success_text": "#155C42", "danger_bg": "#FBEAE3", "danger_text": "#9C4322",
        "warning_bg": "#FCF3DC", "warning_text": "#7A5A0A", "info_bg": "#E9F0EC", "info_text": "#1E4A3A",
        "sidebar": "#123C31", "sidebar_hover": "#1E5C4A", "sidebar_text": "#FFFFFF", "sidebar_active_text": "#FFFFFF",
    },
    "paleta-03": {
        "id": "paleta-03", "numero": "03", "nome": "Grafite & Vinho — Minimalista",
        "descricao": "Grafite neutro com vinho como cor de autoridade, priorizando foco e densidade de informação.",
        "primary": "#2B2B2E", "primary_light": "#45454A", "primary_dark": "#18181A", "accent": "#7A1F2B",
        "background": "#F5F5F4", "paper": "#FFFFFF", "text": "#1A1A1B", "muted": "#6B665C", "line": "#DEDEDC",
        "success_bg": "#E9EFE9", "success_text": "#2C5C36", "danger_bg": "#F6E7E9", "danger_text": "#7A1F2B",
        "warning_bg": "#F3EEDD", "warning_text": "#6E5A16", "info_bg": "#ECECEB", "info_text": "#3A3A3C",
        "sidebar": "#2B2B2E", "sidebar_hover": "#45454A", "sidebar_text": "#FFFFFF", "sidebar_active_text": "#FFFFFF",
    },
    "paleta-04": {
        "id": "paleta-04", "numero": "04", "nome": "Preto Jurídico",
        "descricao": "Preto puro, azul ardósia e dourado discreto para uma presença jurídica sóbria e contundente.",
        "primary": "#111111", "primary_light": "#333333", "primary_dark": "#000000", "accent": "#B08D3E",
        "background": "#F4F4F2", "paper": "#FFFFFF", "text": "#171717", "muted": "#686868", "line": "#D9D9D6",
        "success_bg": "#E7F1EA", "success_text": "#1E5C3E", "danger_bg": "#FBE8E8", "danger_text": "#8C2525",
        "warning_bg": "#FCF3DC", "warning_text": "#755A0A", "info_bg": "#E8EDF2", "info_text": "#33485C",
        "sidebar": "#000000", "sidebar_hover": "#252525", "sidebar_text": "#FFFFFF", "sidebar_active_text": "#FFFFFF",
    },
    "paleta-05": {
        "id": "paleta-05", "numero": "05", "nome": "Azul Névoa Institucional",
        "descricao": "Azul-cinza claro com azul petróleo, superfícies suaves e bronze discreto para uma navegação serena e profissional.",
        "primary": "#274C5E", "primary_light": "#4B7180", "primary_dark": "#193542", "accent": "#A87945",
        "background": "#F3F6F7", "paper": "#FBFCFD", "text": "#243038", "muted": "#68747A", "line": "#C9D7DE",
        "success_bg": "#E6F1EB", "success_text": "#216044", "danger_bg": "#F9E9E4", "danger_text": "#9A3E2F",
        "warning_bg": "#FBF1D9", "warning_text": "#785B13", "info_bg": "#E7EFF1", "info_text": "#315B6B",
        "sidebar": "#E7EEF2", "sidebar_hover": "#D6E2E8", "sidebar_text": "#274C5E", "sidebar_active_text": "#FFFFFF",
    },
    "paleta-06": {
        "id": "paleta-06", "numero": "06", "nome": "Dourado de Ofício",
        "descricao": "Dourado institucional com azul petróleo profundo, remetendo a tradição, autoridade e excelência profissional.",
        "primary": "#244353", "primary_light": "#3C6878", "primary_dark": "#142B36", "accent": "#B58A3A",
        "background": "#F6F1E6", "paper": "#FFFDFC", "text": "#29251F", "muted": "#766E61", "line": "#DDD2BF",
        "success_bg": "#E7F0E8", "success_text": "#356044", "danger_bg": "#F9E9E5", "danger_text": "#963F32",
        "warning_bg": "#FCF1D5", "warning_text": "#765A13", "info_bg": "#E8EFF1", "info_text": "#315B6C",
        "sidebar": "#244353", "sidebar_hover": "#3C6878", "sidebar_text": "#FFFFFF", "sidebar_active_text": "#FFFFFF",
    },
}


def listar_paletas_institucionais() -> list[dict]:
    """Retorna cópias seguras do catálogo para renderização nos templates."""
    return [deepcopy(paleta) for paleta in PALETAS_INSTITUCIONAIS.values()]


def tema_institucional_valido(tema: str | None) -> bool:
    return bool(tema and tema in PALETAS_INSTITUCIONAIS)


def obter_paleta_institucional(tema: str | None) -> dict:
    return deepcopy(PALETAS_INSTITUCIONAIS.get(tema or APPEARANCE_DEFAULT, PALETAS_INSTITUCIONAIS[APPEARANCE_DEFAULT]))
