import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {
    'verificar_tentativas_login', 'registrar_tentativa_login',
    'get_user_by_username', 'update_user_last_login', 'create_user',
    'create_password_reset_token', 'get_password_reset_token',
    'mark_password_reset_token_as_used', 'gravar_auditoria_admin',
    'gravar_tentativa_nao_autorizada',
}
functions = [
    node for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name in targets
]
assert len(functions) == len(targets), (len(functions), sorted(targets))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions, key=lambda item: item.lineno):
    chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
header = '''"""Serviços de usuários, autenticação e auditoria.\n\nAs funções preservam as assinaturas legadas para que as rotas existentes\ncontinuem importando-as através de `models.py`.\n"""\n\nfrom datetime import datetime, timedelta\nimport secrets\nimport sqlite3\n\nimport pytz\n\nfrom data.database import executar_query, get_sqlite_connection\nfrom utils.logger import logger, security_logger\n\nTENTATIVAS_MAX = 5\nBLOQUEIO_TEMPO = 900\n\n'''
Path('data/users.py').write_text(header + ''.join(chunks), encoding='utf-8')

ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
# Add compatibility imports immediately after the existing data imports.
marker = 'from data.migrations import executar_migracoes_dados\n'
compat = '''from data.users import (\n    verificar_tentativas_login, registrar_tentativa_login,\n    get_user_by_username, update_user_last_login, create_user,\n    create_password_reset_token, get_password_reset_token,\n    mark_password_reset_token_as_used, gravar_auditoria_admin,\n    gravar_tentativa_nao_autorizada,\n)\n'''
updated = ''.join(new_lines).replace(marker, marker + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
