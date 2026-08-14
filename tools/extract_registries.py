import ast
from pathlib import Path

models_path = Path('models.py')
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
targets = {
    'listar_titulares', 'get_titular_by_id', 'titular_tem_processos',
    '_sincronizar_processos_cadastro', 'editar_titular', 'excluir_titular',
    'get_historico_servicos_titular', 'upsert_titular_from_processo',
    'buscar_titulares_json', 'listar_apresentantes', 'get_apresentante_by_id',
    'apresentante_tem_processos', 'editar_apresentante', 'excluir_apresentante',
    'get_historico_servicos_apresentante', 'buscar_apresentantes_json',
    'upsert_apresentante_from_processo',
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
header = '''"""Serviços de titulares, apresentantes e sincronização com processos."""\n\nimport math\nfrom datetime import datetime\n\nfrom data.database import executar_query, get_sqlite_connection\nfrom data.processes import registrar_historico_processo\n\n'''
Path('data/registries.py').write_text(header + ''.join(chunks), encoding='utf-8')
ranges = sorted(((node.lineno - 1, node.end_lineno) for node in functions.values()), reverse=True)
new_lines = lines[:]
for start, end in ranges:
    del new_lines[start:end]
needle = 'from data.process_status import (\n'
close = '    add_status_processo, update_status_processo, toggle_status_processo,\n)\n'
compat = '''from data.registries import (\n    listar_titulares, get_titular_by_id, titular_tem_processos,\n    editar_titular, excluir_titular, get_historico_servicos_titular,\n    upsert_titular_from_processo, buscar_titulares_json,\n    listar_apresentantes, get_apresentante_by_id, apresentante_tem_processos,\n    editar_apresentante, excluir_apresentante, get_historico_servicos_apresentante,\n    buscar_apresentantes_json, upsert_apresentante_from_processo,\n)\n'''
updated = ''.join(new_lines).replace(close, close + compat, 1)
models_path.write_text(updated, encoding='utf-8')
print('extracted:', ', '.join(sorted(targets)))
