from pathlib import Path
import re

css = Path('static/css/color-themes.css').read_text(encoding='utf-8')
shared_required = {
    '--rf-text-heading', '--rf-text-primary', '--rf-text-secondary', '--rf-text-muted', '--rf-text-strong',
    '--rf-text-body', '--rf-text-on-primary', '--rf-text-on-sidebar', '--rf-text-link',
    '--rf-bg-cold', '--rf-bg-warm', '--rf-surface-modal',
    '--rf-surface-body', '--rf-surface-card', '--rf-surface-muted', '--rf-surface-input',
    '--rf-surface-hover', '--rf-surface-overlay', '--rf-border', '--rf-border-subtle',
    '--rf-border-input', '--rf-border-strong', '--rf-action-primary',
    '--rf-action-primary-hover', '--rf-action-primary-active', '--rf-action-secondary',
    '--rf-action-secondary-hover', '--rf-accent', '--rf-accent-hover', '--rf-accent-subtle',
    '--rf-danger', '--rf-danger-hover', '--rf-danger-surface', '--rf-danger-text',
    '--rf-success', '--rf-success-hover', '--rf-success-surface', '--rf-success-text',
    '--rf-warning', '--rf-warning-hover', '--rf-warning-surface', '--rf-warning-text',
    '--rf-info', '--rf-info-hover', '--rf-info-surface', '--rf-info-text',
    '--rf-sidebar-surface', '--rf-sidebar-hover', '--rf-sidebar-active', '--rf-sidebar-text',
    '--rf-sidebar-active-text', '--rf-sidebar-border', '--rf-control-height', '--rf-sidebar-width',
}
palette_required = {f'--rf-palette-color-{index}' for index in range(1, 6)}

semantic_match = re.search(r'\[data-cor\^="paleta-"\]\s*\{(?P<body>.*?)\n\}', css, re.S | re.M)
assert semantic_match, 'bloco semântico compartilhado ausente'
semantic_body = semantic_match.group('body')
for token in shared_required:
    assert re.search(rf'{re.escape(token)}\s*:', semantic_body), f'token semântico ausente: {token}'

for number in range(1, 31):
    theme = f'paleta-{number:02d}'
    match = re.search(rf'^\[data-cor="{theme}"\]\s*\{{(?P<body>.*?)\n\}}', css, re.S | re.M)
    assert match, f'{theme}: bloco não encontrado'
    body = match.group('body')
    assert re.search(r'--color-primary\s*:', body), f'{theme}: primary ausente'
    assert re.search(r'--sidebar\s*:', body), f'{theme}: sidebar ausente'
    for token in palette_required:
        assert re.search(rf'{re.escape(token)}\s*:', body), f'{theme}: palette token ausente: {token}'

for line in css.splitlines():
    declarations = re.findall(r'(--[\w-]+)\s*:\s*([^;]+)', line)
    for name, value in declarations:
        assert f'var({name}' not in value, f'alias circular: {name}: {value}'

print('semantic-token-validation: ok; themes=30; required_tokens=', len(shared_required) + len(palette_required))
