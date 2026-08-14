import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'criar_indices_performance')
lines = source.splitlines(keepends=True)
header = '''"""Índices de performance do banco de dados."""\n\nfrom utils.logger import logger\n\n'''
chunk = ''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n'
Path('data/indexes.py').write_text(header + chunk, encoding='utf-8')
new_lines = lines[:]
del new_lines[node.lineno - 1:node.end_lineno]
needle = 'from data.admin_queries import obter_usuarios_para_selecao, get_users_for_admin_list\n'
updated = ''.join(new_lines).replace(needle, needle + 'from data.indexes import criar_indices_performance\n', 1)
models_path.write_text(updated.rstrip() + '\n', encoding='utf-8')
print('extracted: criar_indices_performance')
