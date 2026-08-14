import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {'obter_usuarios_para_selecao', 'get_users_for_admin_list'}
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in targets}
assert set(functions) == targets, sorted(targets - set(functions))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions.values(), key=lambda item: item.lineno):
    chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
header = '''"""Consultas administrativas e seleção de usuários."""\n\nfrom data.database import executar_query\n\n'''
Path('data/admin_queries.py').write_text(header + ''.join(chunks), encoding='utf-8')
ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.logging import gravar_log\n'
compat = '''from data.admin_queries import obter_usuarios_para_selecao, get_users_for_admin_list\n'''
updated = ''.join(new_lines).replace(needle, needle + compat, 1)
models_path.write_text(updated.rstrip() + '\n', encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
