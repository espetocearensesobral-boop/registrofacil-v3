import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {'obter_logs_auditoria'}
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in targets}
assert set(functions) == targets
lines = source.splitlines(keepends=True)
node = functions['obter_logs_auditoria']
header = '''"""Consultas de auditoria administrativa."""\n\nimport math\n\nfrom data.database import executar_query\nfrom utils.logger import logger\n\n'''
chunk = ''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n'
Path('data/audit_logs.py').write_text(header + chunk, encoding='utf-8')
new_lines = lines[:]
del new_lines[node.lineno - 1:node.end_lineno]
needle = 'from data.templates import (\n'
close = '    excluir_template, gerar_senha_temporaria, mascarar_email,\n)\n'
compat = 'from data.audit_logs import obter_logs_auditoria\n'
updated = ''.join(new_lines).replace(close, close + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted: obter_logs_auditoria')
