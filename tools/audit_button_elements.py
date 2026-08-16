from pathlib import Path
import csv
import re
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'templates'
BUTTON_CLASS_RE = re.compile(r'^(?:btn(?:-|$)|nav-btn(?:-|$)|action-btn(?:-|$)|tbl-btn(?:-|$)|rf-tab-btn(?:-|$)|metricas-tab-btn(?:-|$)|cat-toggle-btn(?:-|$)|cfg-|nt-btn-|auth-btn(?:-|$))', re.I)
rows = []

for path in sorted(TEMPLATES.rglob('*.html')):
    source = path.read_text(encoding='utf-8', errors='ignore')
    soup = BeautifulSoup(source, 'html.parser')
    for element in soup.find_all(class_=True):
        classes = element.get('class', [])
        if not any(BUTTON_CLASS_RE.search(cls) for cls in classes):
            continue
        if element.name not in {'button', 'a', 'input', 'span'}:
            continue
        text = ' '.join(element.get_text(' ', strip=True).split())
        if element.name == 'input':
            text = element.get('value', '') or element.get('aria-label', '')
        line = source[:element.sourceline and 0 or 0].count('\n') + 1 if getattr(element, 'sourceline', None) else ''
        rows.append({
            'arquivo': str(path.relative_to(ROOT)),
            'linha': line,
            'tag': element.name,
            'texto': text[:160],
            'href': element.get('href', ''),
            'classes': ' '.join(classes),
            'style_inline': element.get('style', ''),
            'disabled': 'disabled' in element.attrs or element.get('aria-disabled') == 'true',
        })

rows.sort(key=lambda row: (row['arquivo'], str(row['linha']), row['tag'], row['texto']))
out_csv = ROOT / 'docs' / 'button-elements.csv'
with out_csv.open('w', newline='', encoding='utf-8') as handle:
    writer = csv.DictWriter(handle, fieldnames=rows[0].keys() if rows else ['arquivo'], lineterminator='\n')
    writer.writeheader()
    csv_rows = [{key: (value if value not in ('', None) else '-') for key, value in row.items()} for row in rows]
    writer.writerows(csv_rows)

out_md = ROOT / 'docs' / 'button-elements.md'
with out_md.open('w', encoding='utf-8') as handle:
    handle.write('# Inventário elemento a elemento dos botões\n\n')
    handle.write(f'Foram identificados **{len(rows)} elementos** com classes de ação nos templates.\n\n')
    handle.write('| # | Arquivo | Linha | Tag | Texto | Classes | Href | Disabled | Estilo inline |\n')
    handle.write('|---:|---|---:|---|---|---|---|---|---|\n')
    for index, row in enumerate(rows, 1):
        values = [str(index), row['arquivo'], str(row['linha']), row['tag'], row['texto'] or '-', row['classes'] or '-', row['href'] or '-', str(row['disabled']), row['style_inline'] or '-']
        values = [value.replace('|', '\\|').replace('\n', ' ') for value in values]
        handle.write('| ' + ' | '.join(values) + ' |\n')

print(f'button-elements: {len(rows)} elements; markdown={out_md}; csv={out_csv}')
