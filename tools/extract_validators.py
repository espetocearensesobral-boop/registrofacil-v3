import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {'validar_formato_matricula', 'validar_telefone_unico', 'validar_email_unico'}
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in targets}
assert set(functions) == targets, sorted(targets - set(functions))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions.values(), key=lambda item: item.lineno):
    chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
header = '''"""Validações de dados de processos e cadastros."""\n\nimport re\nimport sqlite3\n\nfrom data.database import executar_query\nfrom utils.logger import logger\n\n'''
Path('data/validators.py').write_text(header + ''.join(chunks), encoding='utf-8')
ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.indexes import criar_indices_performance\n'
compat = '''from data.validators import validar_formato_matricula, validar_telefone_unico, validar_email_unico\n'''
updated = ''.join(new_lines).replace(needle, needle + compat, 1)
models_path.write_text(updated.rstrip() + '\n', encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
