import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {'validar_tipo_servico', 'validar_nome_unico_db', 'obter_tipos_servico', 'add_tipo_servico', 'update_tipo_servico', 'toggle_tipo_servico'}
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in targets}
assert set(functions) == targets, sorted(targets - set(functions))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions.values(), key=lambda item: item.lineno):
    chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
header = '''"""Catálogo e administração de tipos de serviço."""\n\nfrom data.database import executar_query\n\n'''
Path('data/catalog.py').write_text(header + ''.join(chunks), encoding='utf-8')
ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.locks import (\n'
close = '    acquire_lock, release_lock, renew_lock, release_all_locks, is_record_locked,\n)\n'
compat = '''from data.catalog import (\n    validar_tipo_servico, validar_nome_unico_db, obter_tipos_servico,\n    add_tipo_servico, update_tipo_servico, toggle_tipo_servico,\n)\n'''
updated = ''.join(new_lines).replace(close, close + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
