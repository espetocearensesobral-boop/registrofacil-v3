from pathlib import Path
import re
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / 'templates'
CSS_DIR = ROOT / 'static' / 'css'

button_re = re.compile(r'<(?:button|a|input|span)\b[^>]*class=["\']([^"\']+)["\'][^>]*>', re.I | re.S)
style_re = re.compile(r'\bstyle=["\']([^"\']+)["\']', re.I | re.S)
class_re = re.compile(r'\b(?:btn|button|nav-btn|action-btn|tbl-btn|rf-tab-btn|metricas-tab-btn|cat-toggle-btn|cfg-[\w-]+|nt-btn-[\w-]+|auth-btn)[\w-]*\b')
css_rule_re = re.compile(r'([^{}]+)\{([^{}]+)\}', re.S)

class_counts = Counter()
class_files = defaultdict(set)
inline = []
markup_count = 0

for path in sorted(TEMPLATES.rglob('*.html')):
    text = path.read_text(encoding='utf-8', errors='ignore')
    for match in button_re.finditer(text):
        markup_count += 1
        classes = sorted(set(class_re.findall(match.group(1))))
        for cls in classes:
            class_counts[cls] += 1
            class_files[cls].add(str(path.relative_to(ROOT)))
        style = style_re.search(match.group(0))
        if style:
            inline.append((str(path.relative_to(ROOT)), classes, style.group(1).strip()))

css_rules = []
for path in sorted(CSS_DIR.glob('*.css')):
    text = path.read_text(encoding='utf-8', errors='ignore')
    for match in css_rule_re.finditer(text):
        selectors, declarations = ' '.join(match.group(1).split()), ' '.join(match.group(2).split())
        if class_re.search(selectors) or re.search(r'\b(?:button|input\[type=|a\.btn)', selectors):
            css_rules.append((str(path.relative_to(ROOT)), selectors, declarations))

out = []
out.append('# Inventário completo de botões')
out.append('')
out.append(f'Elementos com classe de botão encontrados: **{markup_count}**')
out.append('')
out.append('## Classes por frequência')
out.append('')
out.append('| Classe | Ocorrências | Arquivos |')
out.append('|---|---:|---|')
for cls, count in class_counts.most_common():
    files = ', '.join(sorted(class_files[cls]))
    out.append(f'| `{cls}` | {count} | {files} |')
out.append('')
out.append('## Estilos inline em elementos de botão')
out.append('')
out.append('| Arquivo | Classes | Estilo inline |')
out.append('|---|---|---|')
for path, classes, style in inline:
    out.append(f'| `{path}` | `{", ".join(classes)}` | `{style}` |')
out.append('')
out.append('## Regras CSS relacionadas')
out.append('')
out.append('| Arquivo | Seletores | Declarações |')
out.append('|---|---|---|')
for path, selectors, declarations in css_rules:
    if re.search(r'background(?:-color)?\s*:\s*(transparent|#fff|#ffffff|white|var\(--background-color-card\)|var\(--rf-action-secondary\))', declarations, re.I):
        out.append(f'| `{path}` | `{selectors}` | `{declarations}` |')

report = ROOT / 'docs' / 'button-inventory.md'
report.write_text('\n'.join(out) + '\n', encoding='utf-8')
print(f'button-inventory: {markup_count} elements; {len(class_counts)} classes; {len(inline)} inline styles; report={report}')
