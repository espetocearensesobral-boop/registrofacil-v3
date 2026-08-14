import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'gravar_log')
lines = source.splitlines(keepends=True)
header = '''"""Registro de logs de segurança e auditoria."""\n\nfrom data.database import executar_query\nfrom utils.logger import logger, security_logger\n\n'''
chunk = ''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n'
Path('data/logging.py').write_text(header + chunk, encoding='utf-8')
new_lines = lines[:]
del new_lines[node.lineno - 1:node.end_lineno]
needle = 'from data.audit_logs import obter_logs_auditoria\n'
updated = ''.join(new_lines).replace(needle, needle + 'from data.logging import gravar_log\n', 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted: gravar_log')
