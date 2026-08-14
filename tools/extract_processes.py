import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {
    'validar_status', 'get_status_id_by_name', 'create_processo',
    'get_processo_by_id', 'update_processo', 'excluir_processo_db',
    'registrar_historico_processo', 'obter_historico_processo',
    'listar_processos', 'get_total_processes_count',
    'get_concluidos_processes_count', 'get_overdue_processes_count',
    'get_in_progress_processes_count', 'get_today_processes_count',
    'get_prenotados_processes_count', 'get_em_andamento_processes_count',
    'get_user_linked_processes_count', 'get_recent_processes',
    'get_critical_deadline_processes', 'obter_anexos_processo',
    'inserir_anexo_processo', 'excluir_anexo_processo',
}
functions = {
    node.name: node for node in tree.body
    if isinstance(node, ast.FunctionDef) and node.name in targets
}
assert set(functions) == targets, sorted(targets - set(functions))
lines = source.splitlines(keepends=True)
chunks = []
for node in sorted(functions.values(), key=lambda item: item.lineno):
    chunks.append(''.join(lines[node.lineno - 1:node.end_lineno]).rstrip() + '\n\n')
header = '''"""Serviços de processos, histórico e anexos.\n\nAs funções preservam as assinaturas legadas, incluindo o parâmetro\n`connection` usado por operações transacionais.\n"""\n\nimport sqlite3\nfrom datetime import datetime\n\nfrom config import Config\nfrom data.backup import rebuild_fts_index\nfrom data.database import executar_query, get_sqlite_connection\nfrom utils.logger import logger\n\nDATABASE_PATH = Config.DATABASE_PATH\n\n'''
Path('data/processes.py').write_text(header + ''.join(chunks), encoding='utf-8')

ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.backup import (\n'
close = '    init_fts, _ensure_fts_triggers,\n)\n'
compat = '''from data.processes import (\n    validar_status, get_status_id_by_name, create_processo,\n    get_processo_by_id, update_processo, excluir_processo_db,\n    registrar_historico_processo, obter_historico_processo, listar_processos,\n    get_total_processes_count, get_concluidos_processes_count,\n    get_overdue_processes_count, get_in_progress_processes_count,\n    get_today_processes_count, get_prenotados_processes_count,\n    get_em_andamento_processes_count, get_user_linked_processes_count,\n    get_recent_processes, get_critical_deadline_processes,\n    obter_anexos_processo, inserir_anexo_processo, excluir_anexo_processo,\n)\n'''
updated = ''.join(new_lines).replace(close, close + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
