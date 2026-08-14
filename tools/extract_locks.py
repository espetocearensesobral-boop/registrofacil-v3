import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {'acquire_lock', 'release_lock', 'renew_lock', 'release_all_locks', 'is_record_locked'}
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in targets}
assert set(functions) == targets, sorted(targets - set(functions))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions.values(), key=lambda item: item.lineno):
    chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
header = '''"""Locks cooperativos de registros."""\n\nfrom config import Config\nfrom data.database import executar_query\nfrom utils.logger import logger\n\nLOCK_TIMEOUT_MINUTES = 15\n\n'''
Path('data/locks.py').write_text(header + ''.join(chunks), encoding='utf-8')
ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.registries import (\n'
close = '    buscar_apresentantes_json, upsert_apresentante_from_processo,\n)\n'
compat = '''from data.locks import (\n    acquire_lock, release_lock, renew_lock, release_all_locks, is_record_locked,\n)\n'''
updated = ''.join(new_lines).replace(close, close + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
