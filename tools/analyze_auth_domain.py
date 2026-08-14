import ast
from pathlib import Path

source = Path('models.py').read_text(encoding='utf-8')
tree = ast.parse(source)
names = {
    'verificar_tentativas_login', 'registrar_tentativa_login',
    'get_user_by_username', 'update_user_last_login', 'create_user',
    'create_password_reset_token', 'get_password_reset_token',
    'mark_password_reset_token_as_used', 'gravar_auditoria_admin',
    'gravar_tentativa_nao_autorizada',
}
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name in names:
        loaded, assigned = set(), set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                (loaded if isinstance(child.ctx, ast.Load) else assigned).add(child.id)
            elif isinstance(child, ast.FunctionDef):
                assigned.add(child.name)
        print(f'{node.name}: {node.lineno}-{node.end_lineno}')
        print('  livres:', ', '.join(sorted(loaded - assigned)))
