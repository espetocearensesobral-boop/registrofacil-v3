#!/usr/bin/env python3
"""Lint visual mínimo e determinístico para impedir regressões conhecidas de UI."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

FORBIDDEN = (
    r"height\s*:\s*26px",
    r"col-12 d-flex justify-content-end gap-2 mt-3",
    r"#dc3545",
    r"#ff8c00",
    r"#1E88E5",
)
DASHBOARD_GEOMETRY = re.compile(r"style\s*=\s*\"(?![^\"]*--st:)[^\"]*(?:height|width|padding|margin|font-size|display|position|background|border)", re.I)


def main() -> int:
    errors: list[str] = []
    for path in TEMPLATES.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        # O painel de status possui um seletor explícito de cores personalizadas;
        # seus swatches são dados de entrada, não cores aplicadas ao layout.
        lint_text = text if path.name != "configuracoes.html" else re.sub(r"<span class=\"cswatch.*?</span>", "", text, flags=re.S)
        for pattern in FORBIDDEN:
            if re.search(pattern, lint_text):
                errors.append(f"{path.relative_to(ROOT)}: contém padrão proibido {pattern}")
    dashboard = TEMPLATES / "dashboard.html"
    dashboard_text = dashboard.read_text(encoding="utf-8")
    if DASHBOARD_GEOMETRY.search(dashboard_text):
        errors.append("templates/dashboard.html: contém geometria inline; use classes CSS")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("ui-lint: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
