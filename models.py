"""Fachada de compatibilidade da camada de dados.

As implementações ficam organizadas nos módulos de ``data``. Este arquivo
mantém os nomes públicos historicamente importados pelas rotas, utilitários
e integrações do aplicativo.
"""

from config import Config
from utils.helpers import validarCPF, validarCNPJ, validar_telefone, validar_email
from data.database import (
    get_sqlite_connection,
    executar_query,
    add_column_if_not_exists_sqlite,
)
from data.migrations import executar_migracoes_dados
from data.crypto import encrypt, decrypt
from data.users import (
    verificar_tentativas_login,
    registrar_tentativa_login,
    get_user_by_username,
    update_user_last_login,
    create_user,
    create_password_reset_token,
    get_password_reset_token,
    mark_password_reset_token_as_used,
    gravar_auditoria_admin,
    gravar_tentativa_nao_autorizada,
)
from data.configuration import (
    get_config,
    set_config,
    obter_status_processo_config,
    get_email_config,
    save_email_config,
    send_email,
    get_backup_config,
    save_backup_config,
    update_last_backup_time,
)
from data.notifications import (
    criar_notificacao,
    listar_notificacoes_pendentes,
    marcar_notificacao_lida,
    marcar_todas_lidas,
    gerar_notificacoes_prazos,
    obter_preferencias_usuario,
    atualizar_preferencias_usuario,
    criar_notificacao_usuario,
    obter_notificacoes_usuario,
    marcar_notificacao_usuario_lida,
    obter_tema_usuario,
    obter_preferencia_visual_usuario,
    salvar_tema_usuario,
)
from data.backup import (
    get_upload_folder,
    test_db_connection,
    optimize_database,
    check_and_repair_database,
    reconstruct_database,
    rebuild_fts_index,
    init_fts,
    _ensure_fts_triggers,
)
from data.processes import (
    validar_status,
    get_status_id_by_name,
    create_processo,
    get_processo_by_id,
    update_processo,
    excluir_processo_db,
    registrar_historico_processo,
    obter_historico_processo,
    listar_processos,
    get_total_processes_count,
    get_concluidos_processes_count,
    get_overdue_processes_count,
    get_in_progress_processes_count,
    get_today_processes_count,
    get_prenotados_processes_count,
    get_em_andamento_processes_count,
    get_user_linked_processes_count,
    get_recent_processes,
    get_critical_deadline_processes,
    obter_anexos_processo,
    inserir_anexo_processo,
    excluir_anexo_processo,
)
from data.process_status import (
    add_status_processo,
    update_status_processo,
    toggle_status_processo,
)
from data.registries import (
    listar_titulares,
    get_titular_by_id,
    titular_tem_processos,
    editar_titular,
    excluir_titular,
    get_historico_servicos_titular,
    upsert_titular_from_processo,
    buscar_titulares_json,
    listar_apresentantes,
    get_apresentante_by_id,
    apresentante_tem_processos,
    editar_apresentante,
    excluir_apresentante,
    get_historico_servicos_apresentante,
    buscar_apresentantes_json,
    upsert_apresentante_from_processo,
)
from data.locks import (
    acquire_lock,
    release_lock,
    renew_lock,
    release_all_locks,
    is_record_locked,
)
from data.catalog import (
    validar_tipo_servico,
    validar_nome_unico_db,
    obter_tipos_servico,
    add_tipo_servico,
    update_tipo_servico,
    toggle_tipo_servico,
)
from data.company import get_empresa_info, save_empresa_info
from data.search import busca_full_text, busca_tradicional
from data.templates import (
    criar_template,
    listar_templates,
    obter_template,
    atualizar_template,
    excluir_template,
    gerar_senha_temporaria,
    mascarar_email,
)
from data.audit_logs import obter_logs_auditoria
from data.logging import gravar_log
from data.admin_queries import obter_usuarios_para_selecao, get_users_for_admin_list
from data.indexes import criar_indices_performance
from data.validators import (
    validar_formato_matricula,
    validar_telefone_unico,
    validar_email_unico,
)
from data.representatives import (
    listar_representantes,
    get_representante_by_id,
    get_historico_servicos_representante,
    buscar_representantes_json,
    representante_tem_processos,
    editar_representante,
    excluir_representante,
)

# Aliases mantidos por compatibilidade com rotas, scheduler e utilitários.
DATABASE_PATH = Config.DATABASE_PATH
TENTATIVAS_MAX = Config.TENTATIVAS_MAX
BLOQUEIO_TEMPO = Config.BLOQUEIO_TEMPO
UPLOAD_FOLDER = Config.UPLOAD_PROCESSOS_DIR
MAX_FILE_SIZE = Config.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS
LOCK_TIMEOUT_MINUTES = 15


def init_db():
    """Inicializa o banco usando o schema modular, mantendo a API legada."""
    from data.schema import init_db as initialize_schema

    return initialize_schema(
        criar_indices_performance=criar_indices_performance,
        init_fts=init_fts,
    )
