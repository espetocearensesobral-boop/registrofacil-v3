import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {
    'get_upload_folder', 'test_db_connection', 'optimize_database',
    'check_and_repair_database', 'reconstruct_database',
    'rebuild_fts_index', 'init_fts', '_ensure_fts_triggers',
}
functions = {
    node.name: node for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name in targets
}
assert set(functions) == targets, sorted(targets - set(functions))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions.values(), key=lambda item: item.lineno):
    chunk = ''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n'
    if node.name == 'reconstruct_database':
        chunk = chunk.replace('            init_db()\n', '            _init_db_compat()\n')
    chunks.append(chunk)
header = '''"""Operações de backup, manutenção, reconstrução e FTS."""\n\nimport os\nimport sqlite3\nfrom datetime import datetime\n\nfrom config import Config\nfrom data.database import executar_query, get_sqlite_connection\nfrom utils.logger import logger\n\nDATABASE_PATH = Config.DATABASE_PATH\nUPLOAD_FOLDER = Config.UPLOAD_PROCESSOS_DIR\n\ndef _init_db_compat():\n    """Chama a fachada legada sem criar dependência circular no import."""\n    from models import init_db\n    return init_db()\n\n'''
Path('data/backup.py').write_text(header + ''.join(chunks), encoding='utf-8')

ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.notifications import (\n'
# Locate the complete notifications import and insert backup imports after it.
close = '    marcar_notificacao_usuario_lida, obter_tema_usuario, salvar_tema_usuario,\n)\n'
compat = '''from data.backup import (\n    get_upload_folder, test_db_connection, optimize_database,\n    check_and_repair_database, reconstruct_database, rebuild_fts_index,\n    init_fts, _ensure_fts_triggers,\n)\n'''
updated = ''.join(new_lines).replace(close, close + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
