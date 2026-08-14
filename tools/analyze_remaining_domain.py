import ast
from pathlib import Path

source = Path('models.py').read_text(encoding='utf-8')
tree = ast.parse(source)
patterns = ('busca', 'template', 'log', 'senha', 'mascarar', 'selecao', 'admin')
for node in tree.body:
    if not isinstance(node, ast.FunctionDef):
        continue
    if not any(pattern in node.name.lower() for pattern in patterns):
        continue
    loaded, assigned = set(), set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            (loaded if isinstance(child.ctx, ast.Load) else assigned).add(child.id)
        elif isinstance(child, ast.FunctionDef):
            assigned.add(child.name)
    print(f'{node.name}: {node.lineno}-{node.end_lineno}')
    print('  livres:', ', '.join(sorted(loaded - assigned)))
