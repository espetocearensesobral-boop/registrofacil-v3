import ast
from pathlib import Path

root = Path('.')
models_path = root / 'models.py'
source = models_path.read_text(encoding='utf-8')
tree = ast.parse(source)
fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'init_db')
lines = source.splitlines(keepends=True)
function_source = ''.join(lines[fn.lineno - 1:fn.end_lineno])
function_source = function_source.replace(
    'def init_db():',
    'def init_db(criar_indices_performance, init_fts):',
    1,
)
header = '''"""Bootstrap do schema, seeds e migrações do RegistroFácil.\n\nA função recebe callbacks para índices e FTS porque essas implementações\npermanecem em módulos legados durante a migração incremental.\n"""\n\nimport os\nimport sqlite3\n\nfrom config import Config\nfrom utils.logger import logger\nfrom data.database import (\n    get_sqlite_connection,\n    executar_query,\n    add_column_if_not_exists_sqlite,\n)\nfrom data.migrations import executar_migracoes_dados\n\nUPLOAD_FOLDER = Config.UPLOAD_PROCESSOS_DIR\n\n'''
(root / 'data' / 'schema.py').write_text(header + function_source, encoding='utf-8')

start = fn.lineno - 1
end = fn.end_lineno
facade = '''def init_db():\n    """Inicializa o banco usando o módulo de schema, preservando a API legada."""\n    from data.schema import init_db as initialize_schema\n    return initialize_schema(\n        criar_indices_performance=criar_indices_performance,\n        init_fts=init_fts,\n    )\n\n'''
new_source = ''.join(lines[:start]) + facade + ''.join(lines[end:])
models_path.write_text(new_source, encoding='utf-8')
print(f'extracted init_db lines {fn.lineno}-{fn.end_lineno}')
