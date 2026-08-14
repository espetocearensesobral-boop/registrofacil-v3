import ast
from pathlib import Path

source = Path('models.py').read_text(encoding='utf-8')
tree = ast.parse(source)
fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'init_db')
assigned = set()
loaded = set()
for node in ast.walk(fn):
    if isinstance(node, ast.Name):
        (loaded if isinstance(node.ctx, ast.Load) else assigned).add(node.id)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        assigned.add(node.name)
print('linhas:', fn.lineno, fn.end_lineno)
print('livres:', sorted(loaded - assigned))
print('subfuncoes:', [node.name for node in fn.body if isinstance(node, ast.FunctionDef)])
