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
processes = importlib.import_module("data.processes")
process_status = importlib.import_module("data.process_status")
registries = importlib.import_module("data.registries")
locks = importlib.import_module("data.locks")
catalog = importlib.import_module("data.catalog")
company = importlib.import_module("data.company")
search = importlib.import_module("data.search")
templates = importlib.import_module("data.templates")
audit_logs = importlib.import_module("data.audit_logs")
logging_module = importlib.import_module("data.logging")
admin_queries = importlib.import_module("data.admin_queries")
indexes = importlib.import_module("data.indexes")
validators = importlib.import_module("data.validators")

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
    "validar_status", "get_status_id_by_name", "create_processo",
    "get_processo_by_id", "update_processo", "excluir_processo_db",
    "registrar_historico_processo", "obter_historico_processo", "listar_processos",
    "get_total_processes_count", "get_concluidos_processes_count",
    "get_overdue_processes_count", "get_in_progress_processes_count",
    "get_today_processes_count", "get_prenotados_processes_count",
    "get_em_andamento_processes_count", "get_user_linked_processes_count",
    "get_recent_processes", "get_critical_deadline_processes",
    "obter_anexos_processo", "inserir_anexo_processo", "excluir_anexo_processo",
):
    assert getattr(models, name) is getattr(processes, name), name
for name in ("add_status_processo", "update_status_processo", "toggle_status_processo"):
    assert getattr(models, name) is getattr(process_status, name), name
for name in (
    "listar_titulares", "get_titular_by_id", "titular_tem_processos",
    "editar_titular", "excluir_titular", "get_historico_servicos_titular",
    "upsert_titular_from_processo", "buscar_titulares_json",
    "listar_apresentantes", "get_apresentante_by_id", "apresentante_tem_processos",
    "editar_apresentante", "excluir_apresentante", "get_historico_servicos_apresentante",
    "buscar_apresentantes_json", "upsert_apresentante_from_processo",
):
    assert getattr(models, name) is getattr(registries, name), name
for name in ("acquire_lock", "release_lock", "renew_lock", "release_all_locks", "is_record_locked"):
    assert getattr(models, name) is getattr(locks, name), name
for name in ("validar_tipo_servico", "validar_nome_unico_db", "obter_tipos_servico", "add_tipo_servico", "update_tipo_servico", "toggle_tipo_servico"):
    assert getattr(models, name) is getattr(catalog, name), name
for name in ("get_empresa_info", "save_empresa_info"):
    assert getattr(models, name) is getattr(company, name), name
for name in ("busca_full_text", "busca_tradicional"):
    assert getattr(models, name) is getattr(search, name), name
for name in ("criar_template", "listar_templates", "obter_template", "atualizar_template", "excluir_template", "gerar_senha_temporaria", "mascarar_email"):
    assert getattr(models, name) is getattr(templates, name), name
assert models.obter_logs_auditoria is audit_logs.obter_logs_auditoria
assert models.gravar_log is logging_module.gravar_log
assert models.obter_usuarios_para_selecao is admin_queries.obter_usuarios_para_selecao
assert models.get_users_for_admin_list is admin_queries.get_users_for_admin_list
assert models.criar_indices_performance is indexes.criar_indices_performance
for name in ("validar_formato_matricula", "validar_telefone_unico", "validar_email_unico"):
    assert getattr(models, name) is getattr(validators, name), name
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
    assert processes.get_total_processes_count() == 0
    titular_id = registries.upsert_titular_from_processo(
        "Titular Smoke", "88999990000", "titular-smoke@example.com", None
    )
    assert titular_id
    titular_id_again = registries.upsert_titular_from_processo(
        "Titular Smoke", "88999991111", "titular-smoke@example.com", None
    )
    assert titular_id_again == titular_id
    apresentante_id = registries.upsert_apresentante_from_processo(
        "Apresentante Smoke", "88999992222", "apresentante-smoke@example.com", None
    )
    assert apresentante_id
    apresentante_id_again = registries.upsert_apresentante_from_processo(
        "Apresentante Smoke", "88999993333", "apresentante-smoke@example.com", None
    )
    assert apresentante_id_again == apresentante_id
    admin = users.get_user_by_username("admin")
    assert admin and admin["id"]
    users.create_user("Smoke User", "smoke-user@example.com", "smoke-user", "hash", role="user")
    second_user = users.get_user_by_username("smoke-user")
    assert second_user and second_user["id"]
    owner_id, other_user_id = admin["id"], second_user["id"]
    assert locks.acquire_lock("processos", 1, owner_id, 15) is True
    assert locks.is_record_locked("processos", 1, owner_id) is None
    assert locks.is_record_locked("processos", 1, other_user_id)
    assert locks.renew_lock("processos", 1, owner_id, 15).get("success") is True
    assert locks.release_lock("processos", 1, owner_id).get("success") is True
    assert locks.is_record_locked("processos", 1, other_user_id) is None
    service_id = catalog.add_tipo_servico("Serviço Smoke", "Teste", 15)
    assert service_id
    assert catalog.validar_tipo_servico(service_id) is True
    assert validators.validar_formato_matricula("1234567890") is True
    assert validators.validar_formato_matricula("") is True
    catalog.update_tipo_servico(service_id, "Serviço Smoke Atualizado", "Teste", True, 20)
    assert catalog.obter_tipos_servico()
    catalog.toggle_tipo_servico(service_id)
    company.save_empresa_info({
        "cartorio": "Cartório Smoke",
        "oficial": "Oficial Smoke",
        "endereco": "Rua Smoke, 100",
        "email": "empresa-smoke@example.com",
        "telefone": "(88) 99999-4444",
    }, is_new_record=True)
    assert company.get_empresa_info()["cartorio"] == "Cartório Smoke"
    assert search.busca_tradicional("Smoke") == []
    assert templates.mascarar_email("usuario@example.com") == "u***@example.com"
    temporary_password = templates.gerar_senha_temporaria(16)
    assert len(temporary_password) == 16
    template_id = templates.criar_template("Template Smoke", "Descrição", service_id, 1, 30, "Observação", 1, 1)
    assert template_id
    assert templates.obter_template(template_id)
    assert templates.listar_templates(1)
    assert models.obter_logs_auditoria()["total"] >= 0
    assert admin_queries.obter_usuarios_para_selecao()
    admin_list = admin_queries.get_users_for_admin_list({}, 1, 10, "id_desc")
    assert admin_list["total_records"] >= 1
    with sqlite3.connect(temp_db) as conn:
        indexes.criar_indices_performance(conn.cursor())
    backup.DATABASE_PATH = str(temp_db)
    assert backup.test_db_connection() is True
    assert backup.optimize_database() is True

print("smoke_refactor_models: OK")
