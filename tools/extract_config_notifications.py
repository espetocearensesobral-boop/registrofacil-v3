import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
config_names = {
    'get_config', 'set_config', 'obter_status_processo_config',
    'get_email_config', 'save_email_config', 'send_email',
    'get_backup_config', 'save_backup_config', 'update_last_backup_time',
}
notification_names = {
    'criar_notificacao', 'listar_notificacoes_pendentes',
    'marcar_notificacao_lida', 'marcar_todas_lidas',
    'gerar_notificacoes_prazos', 'obter_preferencias_usuario',
    'atualizar_preferencias_usuario', 'criar_notificacao_usuario',
    'obter_notificacoes_usuario', 'marcar_notificacao_usuario_lida',
    'obter_tema_usuario', 'salvar_tema_usuario',
}
all_names = config_names | notification_names
functions = {
    node.name: node for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name in all_names
}
assert set(functions) == all_names, sorted(all_names - set(functions))
lines = source.splitlines(keepends=True)

def render(names, header):
    chunks = []
    for node in sorted((functions[name] for name in names), key=lambda item: item.lineno):
        chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
    return header + ''.join(chunks)

config_header = '''"""Serviços de configuração, e-mail e backup.\n\nAs funções mantêm as assinaturas legadas para compatibilidade com as rotas\ne com o scheduler.\n"""\n\nfrom config import Config\nfrom data.crypto import encrypt, decrypt\nfrom data.database import executar_query\nfrom utils.logger import logger\n\n'''
notification_header = '''"""Serviços de notificações e preferências do usuário."""\n\nfrom data.database import executar_query, get_sqlite_connection\nfrom utils.logger import logger\n\n'''
Path('data/configuration.py').write_text(render(config_names, config_header), encoding='utf-8')
Path('data/notifications.py').write_text(render(notification_names, notification_header), encoding='utf-8')

ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
marker = 'from data.users import (\n'
# Insert compatibility imports after the complete users import block.
needle = '    gravar_tentativa_nao_autorizada,\n)\n'
compat = '''from data.configuration import (\n    get_config, set_config, obter_status_processo_config,\n    get_email_config, save_email_config, send_email,\n    get_backup_config, save_backup_config, update_last_backup_time,\n)\nfrom data.notifications import (\n    criar_notificacao, listar_notificacoes_pendentes,\n    marcar_notificacao_lida, marcar_todas_lidas, gerar_notificacoes_prazos,\n    obter_preferencias_usuario, atualizar_preferencias_usuario,\n    criar_notificacao_usuario, obter_notificacoes_usuario,\n    marcar_notificacao_usuario_lida, obter_tema_usuario, salvar_tema_usuario,\n)\n'''
updated = ''.join(new_lines).replace(needle, needle + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted configuration:', ', '.join(sorted(config_names)))
print('extracted notifications:', ', '.join(sorted(notification_names)))
