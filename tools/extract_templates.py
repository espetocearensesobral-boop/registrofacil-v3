import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {'criar_template', 'listar_templates', 'obter_template', 'atualizar_template', 'excluir_template', 'gerar_senha_temporaria', 'mascarar_email'}
functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in targets}
assert set(functions) == targets, sorted(targets - set(functions))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions.values(), key=lambda item: item.lineno):
    chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
header = '''"""Templates de processos e auxiliares de apresentação."""\n\nimport secrets\nimport string\n\nfrom data.database import executar_query\n\n'''
Path('data/templates.py').write_text(header + ''.join(chunks), encoding='utf-8')
ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.search import busca_full_text, busca_tradicional\n'
compat = '''from data.templates import (\n    criar_template, listar_templates, obter_template, atualizar_template,\n    excluir_template, gerar_senha_temporaria, mascarar_email,\n)\n'''
updated = ''.join(new_lines).replace(needle, needle + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
