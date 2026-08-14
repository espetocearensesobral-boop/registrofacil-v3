"""Validações rápidas da primeira etapa da refatoração de models.py."""
import ast
import importlib
import sqlite3
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
for relative in ("models.py", "data/database.py"):
    ast.parse((root / relative).read_text(encoding="utf-8"), filename=relative)

models = importlib.import_module("models")
database = importlib.import_module("data.database")
crypto = importlib.import_module("data.crypto")
migrations = importlib.import_module("data.migrations")
users = importlib.import_module("data.users")
configuration = importlib.import_module("data.configuration")
notifications = importlib.import_module("data.notifications")
backup = importlib.import_module("data.backup")

assert models.get_sqlite_connection is database.get_sqlite_connection
assert models.executar_query is database.executar_query
assert models.add_column_if_not_exists_sqlite is database.add_column_if_not_exists_sqlite
assert models.encrypt is crypto.encrypt
assert models.decrypt is crypto.decrypt
assert models.executar_migracoes_dados is migrations.executar_migracoes_dados
for name in (
    "verificar_tentativas_login", "registrar_tentativa_login",
    "get_user_by_username", "update_user_last_login", "create_user",
    "create_password_reset_token", "get_password_reset_token",
    "mark_password_reset_token_as_used", "gravar_auditoria_admin",
    "gravar_tentativa_nao_autorizada",
):
    assert getattr(models, name) is getattr(users, name), name
for module, names in (
    (configuration, (
        "get_config", "set_config", "obter_status_processo_config",
        "get_email_config", "save_email_config", "send_email",
        "get_backup_config", "save_backup_config", "update_last_backup_time",
    )),
    (notifications, (
        "criar_notificacao", "listar_notificacoes_pendentes",
        "marcar_notificacao_lida", "marcar_todas_lidas", "gerar_notificacoes_prazos",
        "obter_preferencias_usuario", "atualizar_preferencias_usuario",
        "criar_notificacao_usuario", "obter_notificacoes_usuario",
        "marcar_notificacao_usuario_lida", "obter_tema_usuario", "salvar_tema_usuario",
    )),
):
    for name in names:
        assert getattr(models, name) is getattr(module, name), name
for name in (
    "get_upload_folder", "test_db_connection", "optimize_database",
    "check_and_repair_database", "reconstruct_database", "rebuild_fts_index",
    "init_fts", "_ensure_fts_triggers",
):
    assert getattr(models, name) is getattr(backup, name), name
secret = "senha-de-teste"
ciphertext = models.encrypt(secret)
assert ciphertext and ciphertext != secret
assert models.decrypt(ciphertext) == secret
assert models.encrypt(None) is None
assert models.decrypt(None) is None
assert hasattr(models, "init_db")
assert hasattr(models, "get_user_by_username")

with tempfile.TemporaryDirectory() as temp_dir:
    temp_db = Path(temp_dir) / "registrofacil-test.db"
    database.DATABASE_PATH = str(temp_db)
    migrations.DATABASE_PATH = str(temp_db)
    models.init_db()
    with sqlite3.connect(temp_db) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {"usuarios", "processos", "titulares"}.issubset(tables)
    backup.DATABASE_PATH = str(temp_db)
    assert backup.test_db_connection() is True
    assert backup.optimize_database() is True

print("smoke_refactor_models: OK")
