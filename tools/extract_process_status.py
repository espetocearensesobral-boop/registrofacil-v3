import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {'add_status_processo', 'update_status_processo', 'toggle_status_processo'}
functions = {
    node.name: node for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name in targets
}
assert set(functions) == targets, sorted(targets - set(functions))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions.values(), key=lambda item: item.lineno):
    chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
header = '''"""Serviços de configuração de status dos processos."""\n\nfrom data.database import executar_query\nfrom utils.logger import logger\n\n'''
Path('data/process_status.py').write_text(header + ''.join(chunks), encoding='utf-8')
ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.processes import (\n'
close = '    obter_anexos_processo, inserir_anexo_processo, excluir_anexo_processo,\n)\n'
compat = '''from data.process_status import (\n    add_status_processo, update_status_processo, toggle_status_processo,\n)\n'''
updated = ''.join(new_lines).replace(close, close + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
