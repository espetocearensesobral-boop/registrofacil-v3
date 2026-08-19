"""Bootstrap do schema, seeds e migrações do RegistroFácil.

A função recebe callbacks para índices e FTS porque essas implementações
permanecem em módulos legados durante a migração incremental.
"""

import os
import sqlite3

from config import Config
from utils.logger import logger
from data.database import (
    get_sqlite_connection,
    executar_query,
    add_column_if_not_exists_sqlite,
)
from data.migrations import executar_migracoes_dados

UPLOAD_FOLDER = Config.UPLOAD_PROCESSOS_DIR

def init_db(criar_indices_performance, init_fts):
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()

        def table_exists(table_name):
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
            return cursor.fetchone() is not None
        
        # NOTE: add_column_if_not_exists_sqlite is now defined outside init_db
        # and has its own get_sqlite_connection context.
        # This prevents issues with 'cursor' not being directly accessible here.
        
        if not table_exists("usuarios"):
            cursor.execute("""
                CREATE TABLE usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    usuario TEXT NOT NULL UNIQUE,
                    senha TEXT NOT NULL,
                    ativo INTEGER DEFAULT 1,
                    role TEXT DEFAULT 'user' NOT NULL,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT,
                    deleted_at TEXT,
                    last_login_at TEXT,
                    session_invalidate_at TEXT, -- Compatibilidade com sessões antigas
                    session_epoch INTEGER DEFAULT 0 NOT NULL, -- Revoga sessões após senha, role, status ou permissões
                    must_change_password INTEGER DEFAULT 0 -- 1 = exige troca de senha no próximo login
                );
            """)
            logger.info("Tabela 'usuarios' criada no SQLite.")
        else:
            logger.info("Tabela 'usuarios' já existe. Verificando/adicionando colunas.")
            add_column_if_not_exists_sqlite('usuarios', 'updated_at', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
            add_column_if_not_exists_sqlite('usuarios', 'deleted_at', 'TEXT')
            add_column_if_not_exists_sqlite('usuarios', 'role', "TEXT DEFAULT 'user' NOT NULL")
            add_column_if_not_exists_sqlite('usuarios', 'last_login_at', 'TEXT')
            # Mantido aqui como fallback para bases de dados mais antigas que já existiam antes da mudança no CREATE TABLE
            add_column_if_not_exists_sqlite('usuarios', 'session_invalidate_at', 'TEXT')
            add_column_if_not_exists_sqlite('usuarios', 'session_epoch', 'INTEGER', default_value='0')
            add_column_if_not_exists_sqlite('usuarios', 'must_change_password', 'INTEGER', default_value='0')

        if not table_exists("login_attempts"):
            cursor.execute("""
                CREATE TABLE login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip TEXT NOT NULL,
                    sucesso INTEGER NOT NULL,
                    tempo TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
                );
            """)
            logger.info("Tabela 'login_attempts' criada no SQLite.")
        else:
            logger.info("Tabela 'login_attempts' já existe.")

        if not table_exists("logs"):
            cursor.execute("""
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acao TEXT NOT NULL,
                    contexto TEXT,
                    processo_id INTEGER,
                    usuario_id INTEGER,
                    ip TEXT,
                    timestamp TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                    FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE
                );
            """)
            logger.info("Tabela 'logs' criada no SQLite.")
        else:
            logger.info("Tabela 'logs' já existe.")
            add_column_if_not_exists_sqlite('logs', 'processo_id', 'INTEGER')
            add_column_if_not_exists_sqlite('logs', 'contexto', 'TEXT')


        if not table_exists("configuracoes"):
            cursor.execute("""
                CREATE TABLE configuracoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chave TEXT NOT NULL UNIQUE,
                    valor TEXT,
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
                );
            """)
            logger.info("Tabela 'configuracoes' criada no SQLite.")
        else:
            logger.info("Tabela 'configuracoes' já existe.")

        if not table_exists("tipos_servico"):
            cursor.execute("""
                CREATE TABLE tipos_servico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    descricao TEXT,
                    ativo INTEGER DEFAULT 1,
                    prazo_padrao INTEGER DEFAULT 30
                );
            """)
            logger.info("Tabela 'tipos_servico' criada no SQLite.")
        else:
            logger.info("Tabela 'tipos_servico' já existe. Verificando/adicionando colunas.")
            add_column_if_not_exists_sqlite('tipos_servico', 'descricao', 'TEXT')
            add_column_if_not_exists_sqlite('tipos_servico', 'ativo', 'INTEGER', default_value=1)
            add_column_if_not_exists_sqlite('tipos_servico', 'prazo_padrao', 'INTEGER', default_value=30)


        if not table_exists("status_processo"):
            cursor.execute("""
                CREATE TABLE status_processo (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    hex_color TEXT DEFAULT '#6c757d',
                    ativo INTEGER DEFAULT 1
                );
            """)
            logger.info("Tabela 'status_processo' criada no SQLite.")
        else:
            logger.info("Tabela 'status_processo' já existe.")
            add_column_if_not_exists_sqlite('status_processo', 'hex_color', 'TEXT', default_value="'#6c757d'")
            add_column_if_not_exists_sqlite('status_processo', 'ativo', 'INTEGER', default_value=1)


        if not table_exists("titulares"):
            cursor.execute("""
                CREATE TABLE titulares (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    telefone TEXT,
                    email TEXT,
                    ultimo_registro_id INTEGER,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (ultimo_registro_id) REFERENCES processos(id) ON DELETE SET NULL
                );
            """)
            logger.info("Tabela 'titulares' criada no SQLite.")
        else:
            logger.info("Tabela 'titulares' já existe.")

        if not table_exists("apresentantes"):
            cursor.execute("""
                CREATE TABLE apresentantes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    telefone TEXT,
                    email TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
                );
            """)
            logger.info("Tabela 'apresentantes' criada no SQLite.")
        else:
            logger.info("Tabela 'apresentantes' já existe.")

        if not table_exists("processos"):
            cursor.execute("""
                CREATE TABLE processos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_processo TEXT NOT NULL UNIQUE,
                    titular TEXT NOT NULL,
                    titular_id INTEGER,
                    titular_telefone TEXT,
                    titular_email TEXT,
                    matricula TEXT,
                    possui_matricula INTEGER DEFAULT 0,
                    tipo_id INTEGER NOT NULL,
                    data_entrada TEXT DEFAULT (strftime('%Y-%m-%d', 'now', 'localtime')),
                    status_id INTEGER NOT NULL,
                    prazo_final TEXT,
                    apresentante TEXT,
                    apresentante_id INTEGER,
                    apresentante_telefone TEXT,
                    apresentante_email TEXT,
                    responsavel_id INTEGER,
                    envolvido_notas INTEGER DEFAULT 0,
                    observacoes TEXT,
                    data_conclusao TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (tipo_id) REFERENCES tipos_servico(id),
                    FOREIGN KEY (status_id) REFERENCES status_processo(id),
                    FOREIGN KEY (responsavel_id) REFERENCES usuarios(id) ON DELETE SET NULL
                );
            """)
            logger.info("Tabela 'processos' criada no SQLite.")
        else:
            logger.info("Tabela 'processos' já existe. Verificando/adicionando colunas.")
            add_column_if_not_exists_sqlite('processos', 'numero_processo', 'TEXT UNIQUE')
            add_column_if_not_exists_sqlite('processos', 'matricula', 'TEXT')
            add_column_if_not_exists_sqlite('processos', 'possui_matricula', 'INTEGER', default_value=0)
            add_column_if_not_exists_sqlite('processos', 'apresentante_telefone', 'TEXT')
            add_column_if_not_exists_sqlite('processos', 'apresentante_email', 'TEXT')
            add_column_if_not_exists_sqlite('processos', 'titular_telefone', 'TEXT')
            add_column_if_not_exists_sqlite('processos', 'titular_email', 'TEXT')
            add_column_if_not_exists_sqlite('processos', 'titular_id', 'INTEGER')
            add_column_if_not_exists_sqlite('processos', 'apresentante_id', 'INTEGER')
            add_column_if_not_exists_sqlite('processos', 'envolvido_notas', 'INTEGER', default_value=0)
            cursor.execute("""
                UPDATE processos
                   SET titular_id = (SELECT id FROM titulares WHERE titulares.nome = processos.titular)
                 WHERE titular_id IS NULL
                   AND titular IS NOT NULL
            """)
            cursor.execute("""
                UPDATE processos
                   SET apresentante_id = (SELECT id FROM apresentantes WHERE apresentantes.nome = processos.apresentante)
                 WHERE apresentante_id IS NULL
                   AND apresentante IS NOT NULL
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processos_titular_id ON processos(titular_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_processos_apresentante_id ON processos(apresentante_id)")
            add_column_if_not_exists_sqlite('processos', 'observacoes', 'TEXT')
            add_column_if_not_exists_sqlite('processos', 'data_conclusao', 'TEXT')
            add_column_if_not_exists_sqlite('processos', 'updated_at', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")


        if not table_exists("anexos_processos"):
            cursor.execute("""
                CREATE TABLE anexos_processos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    processo_id INTEGER NOT NULL,
                    nome_original TEXT NOT NULL,
                    nome_arquivo TEXT NOT NULL UNIQUE,
                    tipo TEXT NOT NULL,
                    tamanho INTEGER NOT NULL,
                    data_upload TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    usuario_upload INTEGER,
                    FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE,
                    FOREIGN KEY (usuario_upload) REFERENCES usuarios(id) ON DELETE SET NULL
                );
            """)
            logger.info("Tabela 'anexos_processos' criada no SQLite.")
        else:
            logger.info("Tabela 'anexos_processos' já existe.")

        if not table_exists("historico_processos"):
            cursor.execute("""
                CREATE TABLE historico_processos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    processo_id INTEGER NOT NULL,
                    usuario_id INTEGER,
                    campo_alterado TEXT,
                    valor_antigo TEXT,
                    valor_novo TEXT,
                    observacao_adicional TEXT,
                    timestamp_alteracao TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
                );
            """)
            logger.info("Tabela 'historico_processos' criada no SQLite.")
        else:
            logger.info("Tabela 'historico_processos' já existe.")
            add_column_if_not_exists_sqlite('historico_processos', 'observacao_adicional', 'TEXT')


        if not table_exists("email_config"):
            cursor.execute("""
                CREATE TABLE email_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    smtp_host TEXT NOT NULL,
                    smtp_port INTEGER NOT NULL,
                    smtp_encryption TEXT NOT NULL,
                    smtp_username TEXT NOT NULL UNIQUE,
                    smtp_password TEXT,
                    sender_email TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    ativo INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
                );
            """)
            logger.info("Tabela 'email_config' criada no SQLite.")
        else:
            logger.info("Tabela 'email_config' já existe.")

        if not table_exists("empresa"):
            cursor.execute("""
                CREATE TABLE empresa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cartorio TEXT NOT NULL,
                    oficial TEXT NOT NULL,
                    substituta TEXT,
                    endereco TEXT NOT NULL,
                    telefone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    logo TEXT, 
                    criado_em TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    atualizado_em TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
                );
            """)
            logger.info("Tabela 'empresa' criada no SQLite com nova estrutura.")
        else:
            logger.info("Tabela 'empresa' já existe. Verificando/adicionando/removendo colunas (se suportado).")
            add_column_if_not_exists_sqlite('empresa', 'cartorio', 'TEXT')
            add_column_if_not_exists_sqlite('empresa', 'oficial', 'TEXT')
            add_column_if_not_exists_sqlite('empresa', 'substituta', 'TEXT')
            add_column_if_not_exists_sqlite('empresa', 'endereco', 'TEXT')
            add_column_if_not_exists_sqlite('empresa', 'telefone', 'TEXT')
            add_column_if_not_exists_sqlite('empresa', 'email', 'TEXT')
            add_column_if_not_exists_sqlite('empresa', 'logo', 'TEXT')
            add_column_if_not_exists_sqlite('empresa', 'criado_em', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
            add_column_if_not_exists_sqlite('empresa', 'atualizado_em', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")


        if not table_exists("record_locks"):
            cursor.execute("""
                CREATE TABLE record_locks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    locked_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    expires_at TEXT NOT NULL,
                    UNIQUE (table_name, record_id),
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
                );
            """)
            logger.info("Tabela 'record_locks' criada no SQLite.")
        else:
            logger.info("Tabela 'record_locks' já existe.")
            add_column_if_not_exists_sqlite('record_locks', 'locked_at', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
            add_column_if_not_exists_sqlite('record_locks', 'expires_at', 'TEXT')

        if not table_exists("backup_configs"):
            cursor.execute("""
                CREATE TABLE backup_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_path TEXT NOT NULL DEFAULT '',
                    cloud_provider TEXT DEFAULT 'none',
                    sftp_host TEXT,
                    sftp_port INTEGER,
                    sftp_username TEXT,
                    sftp_password TEXT,
                    sftp_remote_path TEXT,
                    auto_backup_enabled INTEGER DEFAULT 0,
                    backup_frequency TEXT,
                    backup_time TEXT,
                    backup_days TEXT,
                    backup_day_of_month INTEGER,
                    last_backup_at TEXT,
                    uploads_path TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
                );
            """)
            logger.info("Tabela 'backup_configs' criada no SQLite.")
            cursor.execute("""
                INSERT INTO backup_configs (local_path, cloud_provider, auto_backup_enabled, backup_frequency, backup_time, backup_days, backup_day_of_month, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            """, [Config.DEFAULT_BACKUP_PATH, 'none', 0, 'daily', '02:00', '', 1])
            logger.info("Configuração de backup padrão inserida na tabela 'backup_configs'.")
        else:
            logger.info("Tabela 'backup_configs' já existe. Verificando/adicionando colunas.")
            add_column_if_not_exists_sqlite('backup_configs', 'local_path', "TEXT NOT NULL DEFAULT ''")
            add_column_if_not_exists_sqlite('backup_configs', 'cloud_provider', "TEXT DEFAULT 'none'")
            add_column_if_not_exists_sqlite('backup_configs', 'sftp_host', 'TEXT')
            add_column_if_not_exists_sqlite('backup_configs', 'sftp_port', 'INTEGER')
            add_column_if_not_exists_sqlite('backup_configs', 'sftp_username', 'TEXT')
            add_column_if_not_exists_sqlite('backup_configs', 'sftp_password', 'TEXT')
            add_column_if_not_exists_sqlite('backup_configs', 'sftp_remote_path', 'TEXT')
            add_column_if_not_exists_sqlite('backup_configs', 'auto_backup_enabled', 'INTEGER', default_value=0)
            add_column_if_not_exists_sqlite('backup_configs', 'backup_frequency', 'TEXT')
            add_column_if_not_exists_sqlite('backup_configs', 'backup_time', 'TEXT')
            add_column_if_not_exists_sqlite('backup_configs', 'backup_days', 'TEXT')
            add_column_if_not_exists_sqlite('backup_configs', 'backup_day_of_month', 'INTEGER')
            add_column_if_not_exists_sqlite('backup_configs', 'last_backup_at', 'TEXT')
            add_column_if_not_exists_sqlite('backup_configs', 'uploads_path', 'TEXT')
            # Migração: limpa uploads_path obsoleto do banco.
            # Antes, get_upload_folder() lia esse campo e podia retornar um caminho
            # inconsistente (ex: static/uploads/processos configurado manualmente).
            # Agora o caminho é sempre determinado por Config.UPLOAD_PROCESSOS_DIR.
            try:
                executar_query("UPDATE backup_configs SET uploads_path = NULL WHERE uploads_path IS NOT NULL")
                logger.info("Migração: campo uploads_path limpo da tabela backup_configs.")
            except Exception:
                pass
            add_column_if_not_exists_sqlite('backup_configs', 'created_at', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
            add_column_if_not_exists_sqlite('backup_configs', 'updated_at', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")

        if not table_exists("password_reset_tokens"):
            cursor.execute("""
                CREATE TABLE password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    short_id TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (user_id) REFERENCES usuarios(id) ON DELETE CASCADE
                );
            """)
            logger.info("Tabela 'password_reset_tokens' criada no SQLite.")
        else:
            logger.info("Tabela 'password_reset_tokens' já existe. Verificando/adicionando colunas.")
            add_column_if_not_exists_sqlite('password_reset_tokens', 'is_used', 'INTEGER', default_value=0)
            add_column_if_not_exists_sqlite('password_reset_tokens', 'created_at', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
            add_column_if_not_exists_sqlite('password_reset_tokens', 'updated_at', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
            add_column_if_not_exists_sqlite('password_reset_tokens', 'short_id', 'TEXT')

        logger.info("Esquema do banco de dados SQLite inicializado/verificado com sucesso.")
        conn.commit()  # Garantir que o schema está salvo antes das migrações

        # Executar migrações automáticas de dados
        try:
            executar_migracoes_dados()
        except Exception as e:
            logger.error(f"Erro ao executar migrações de dados: {e}", exc_info=True)
        
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        logger.info(f"Diretório de upload de anexos verificado/criado: {UPLOAD_FOLDER}")

        try:
            cursor.execute("SELECT COUNT(*) FROM tipos_servico;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Abertura de Matrícula", "Criação de nova matrícula de imóvel", 1, 30))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Averbação", "Averbação de documentos ou alterações em registros", 1, 30))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Desmembramento", "Desmembramento de área registrada", 1, 30))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Desm/Escritura/Registro", "Processo que envolve desmembramento, escritura e registro", 1, 60))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Escritura", "Serviço de escritura pública", 1, 45))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Outros", "Serviços diversos não listados", 1, 30)) 
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Procuração Ata Notarial", "Procuração ou ata notarial registrada no sistema", 1, 15))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("RCPJ", "Registro Civil de Pessoas Jurídicas (RCPJ)", 1, 20))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Registro", "Registro de documentos ou imóveis", 1, 30))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("Retificação", "Retificação de registro ou documento", 1, 90))
                cursor.execute("INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)", ("RTD", "Registro de Títulos e Documentos (RTD)", 1, 10))
                logger.info("Tipos de serviço padrão inseridos.")
        except sqlite3.Error as e:
            logger.error(f"Erro ao verificar/inserir tipos de serviço padrão: {e}")
            raise

        try:
            cursor.execute("SELECT COUNT(*) FROM status_processo;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)", ("Aguardando Pagamento", "#ff7300", 1))
                cursor.execute("INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)", ("Analisado", "#ffc107", 1))
                cursor.execute("INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)", ("Finalizado", "#198754", 1))
                cursor.execute("INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)", ("Pago", "#0d6efd", 1))
                cursor.execute("INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)", ("Pendente Análise", "#dc3545", 1))
                cursor.execute("INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)", ("Pendente Documentação", "#6c757d", 1))
                cursor.execute("INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)", ("Prenotado", "#212529", 1))
                cursor.execute("INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)", ("Retirado", "#d71dd1", 1))
                logger.info("Status de processo padrão inseridos.")
        except sqlite3.Error as e:
            logger.error(f"Erro ao verificar/inserir status de processo padrão: {e}")
            raise

        try:
            cursor.execute("SELECT COUNT(*) FROM usuarios WHERE usuario = 'admin'")
            if cursor.fetchone()[0] == 0:
                from werkzeug.security import generate_password_hash
                senha_inicial = Config.INITIAL_ADMIN_PASSWORD
                if not senha_inicial:
                    if Config.IS_PRODUCTION:
                        raise RuntimeError(
                            "INITIAL_ADMIN_PASSWORD deve ser definido antes da primeira inicialização em produção."
                        )
                    senha_inicial = 'admin123'
                    logger.warning(
                        "Senha administrativa de desenvolvimento usada; altere-a no primeiro acesso."
                    )
                senha_hash = generate_password_hash(senha_inicial)
                cursor.execute(
                    "INSERT INTO usuarios (nome, email, usuario, senha, ativo, role, must_change_password, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))",
                    ['Administrador', 'admin@exemplo.com', 'admin', senha_hash, 1, 'admin', 1]
                )
                logger.info("Usuário administrativo inicial criado com troca de senha obrigatória no primeiro acesso.")
            else:
                cursor.execute("UPDATE usuarios SET role = 'admin' WHERE usuario = 'admin' AND (role IS NULL OR role != 'admin')")
                if cursor.rowcount > 0:
                    logger.info("Role do usuário 'admin' atualizada para 'admin'.")
                else:
                    logger.info("Usuário de teste 'admin' já existe e possui a role 'admin'.")
        except sqlite3.Error as e:
            logger.error(f"Erro ao criar/atualizar usuário de teste 'admin' no SQLite: {e}")
            raise

        # ============================================
        # NOVAS TABELAS - v3.2.3+
        # ============================================
        
        # Templates de Processos
        if not table_exists("templates_processos"):
            cursor.execute('''
                CREATE TABLE templates_processos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    descricao TEXT,
                    tipo_id INTEGER NOT NULL,
                    status_id INTEGER,
                    prazo_dias INTEGER DEFAULT 30,
                    observacoes_padrao TEXT,
                    usuario_criador INTEGER,
                    publico INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (tipo_id) REFERENCES tipos_servico(id) ON DELETE CASCADE,
                    FOREIGN KEY (status_id) REFERENCES status_processo(id) ON DELETE SET NULL,
                    FOREIGN KEY (usuario_criador) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            ''')
            logger.info("Tabela 'templates_processos' criada no SQLite.")
        else:
            logger.info("Tabela 'templates_processos' já existe.")

        # Notificações
        if not table_exists("notificacoes"):
            cursor.execute('''
                CREATE TABLE notificacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    mensagem TEXT NOT NULL,
                    processo_id INTEGER,
                    url TEXT,
                    lida INTEGER DEFAULT 0,
                    prioridade TEXT DEFAULT 'normal',
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    read_at TEXT,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE
                )
            ''')
            logger.info("Tabela 'notificacoes' criada no SQLite.")
        else:
            logger.info("Tabela 'notificacoes' já existe.")

        # Preferências do Usuário
        if not table_exists("user_preferences"):
            cursor.execute('''
                CREATE TABLE user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL UNIQUE,
                    tema TEXT DEFAULT 'light',
                    tema_cor TEXT DEFAULT 'paleta-01',
                    notificacoes_push INTEGER DEFAULT 1,
                    notificacoes_email INTEGER DEFAULT 1,
                    dashboard_layout TEXT,
                    filtros_salvos TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
                )
            ''')
            logger.info("Tabela 'user_preferences' criada no SQLite.")
        else:
            add_column_if_not_exists_sqlite("user_preferences", "tema_cor", "TEXT", "paleta-01")
            cursor.execute("UPDATE user_preferences SET tema_cor = 'paleta-01' WHERE tema_cor IS NULL OR tema_cor = 'grafite-vinho' OR tema_cor NOT IN ('paleta-01', 'paleta-02', 'paleta-03', 'paleta-04', 'paleta-05', 'paleta-06', 'paleta-07', 'paleta-08', 'paleta-09', 'paleta-10', 'paleta-11', 'paleta-12', 'paleta-13', 'paleta-14', 'paleta-15', 'paleta-16', 'paleta-17', 'paleta-18', 'paleta-19', 'paleta-20', 'paleta-21', 'paleta-22', 'paleta-23', 'paleta-24', 'paleta-25', 'paleta-26', 'paleta-27', 'paleta-28', 'paleta-29', 'paleta-30')")

            logger.info("Tabela 'user_preferences' já existe.")

        # ============================================
        # SISTEMA DE PERMISSÕES GRANULARES - v3.3.5
        # ============================================
        
        # Módulos do Sistema
        if not table_exists("modulos_sistema"):
            cursor.execute('''
                CREATE TABLE modulos_sistema (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    descricao TEXT,
                    categoria TEXT NOT NULL,
                    ordem INTEGER DEFAULT 0,
                    ativo INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
                )
            ''')
            logger.info("Tabela 'modulos_sistema' criada no SQLite.")
        
        # Inserir módulos padrão do sistema (ou novos módulos)
        modulos = [
            # Processos
            ('processos_visualizar', 'Visualizar lista de processos', 'Processos', 1),
            ('processos_criar', 'Criar novos processos', 'Processos', 2),
            ('processos_editar', 'Editar processos existentes', 'Processos', 3),
            ('processos_excluir', 'Excluir processos', 'Processos', 4),
            ('processos_anexos', 'Gerenciar anexos de processos', 'Processos', 5),
            ('processos_historico', 'Ver histórico de alterações', 'Processos', 6),
            ('processos_exportar', 'Exportar processos para Excel', 'Processos', 7),
            ('processos_imprimir', 'Imprimir lista de processos', 'Processos', 8),
            ('processos_pdf', 'Gerar PDF de processos', 'Processos', 9),
            ('processos_relatorio', 'Gerar relatórios de processos', 'Processos', 10),

            # Titulares
            ('titulares_visualizar', 'Visualizar lista de titulares', 'Titulares', 20),
            ('titulares_criar', 'Criar novos titulares', 'Titulares', 21),
            ('titulares_editar', 'Editar titulares existentes', 'Titulares', 22),
            ('titulares_excluir', 'Excluir titulares', 'Titulares', 23),
            ('titulares_exportar', 'Exportar titulares para Excel', 'Titulares', 24),
            ('titulares_imprimir', 'Imprimir lista de titulares', 'Titulares', 25),

            # Apresentantes
            ('apresentantes_visualizar', 'Visualizar lista de apresentantes', 'Apresentantes', 26),
            ('apresentantes_criar', 'Criar novos apresentantes', 'Apresentantes', 27),
            ('apresentantes_editar', 'Editar apresentantes existentes', 'Apresentantes', 28),
            ('apresentantes_excluir', 'Excluir apresentantes', 'Apresentantes', 29),
            ('apresentantes_exportar', 'Exportar apresentantes para Excel', 'Apresentantes', 30),
            ('apresentantes_imprimir', 'Imprimir lista de apresentantes', 'Apresentantes', 31),

            # Atividades
            ('atividades_visualizar', 'Visualizar histórico de atividades', 'Atividades', 30),
            ('atividades_exportar', 'Exportar log de atividades', 'Atividades', 31),

            # Métricas e Relatórios
            ('metricas_visualizar', 'Visualizar métricas e dashboards', 'Métricas', 40),
            ('relatorios_geral', 'Acessar relatórios gerais', 'Métricas', 41),
            ('relatorios_exportar', 'Exportar relatórios', 'Métricas', 42),

            # Configurações
            ('config_geral', 'Acessar configurações gerais do sistema', 'Configurações', 50),
            ('config_status', 'Gerenciar status de processos', 'Configurações', 51),
            ('config_tipos_servicos', 'Gerenciar tipos de serviço', 'Configurações', 52),
            ('config_email', 'Configurar e-mail do sistema', 'Configurações', 53),
            ('config_empresa', 'Editar dados da empresa', 'Configurações', 54),

            # Backup
            ('backup_visualizar', 'Visualizar página de backup', 'Backup', 60),
            ('backup_criar', 'Criar backups manuais', 'Backup', 61),
            ('backup_download', 'Baixar arquivos de backup', 'Backup', 62),
            ('backup_excluir', 'Excluir arquivos de backup', 'Backup', 63),
            ('backup_config', 'Configurar backup automático', 'Backup', 64),

            # Empresa
            ('empresa_visualizar', 'Visualizar dados da empresa', 'Empresa', 70),
            ('empresa_editar', 'Editar dados da empresa', 'Empresa', 71),

            # Administração de Usuários
            ('admin_usuarios_visualizar', 'Visualizar lista de usuários', 'Administração', 80),
            ('admin_usuarios_criar', 'Criar novos usuários', 'Administração', 81),
            ('admin_usuarios_editar', 'Editar dados de usuários', 'Administração', 82),
            ('admin_usuarios_excluir', 'Excluir usuários', 'Administração', 83),
            ('admin_usuarios_ativar', 'Ativar/desativar usuários', 'Administração', 84),
            ('admin_usuarios_senha', 'Resetar senha de usuários', 'Administração', 85),
            ('admin_permissoes', 'Gerenciar permissões de usuários', 'Administração', 86),
            ('admin_perfis', 'Gerenciar perfis de permissão', 'Administração', 87),
            ('admin_logs', 'Visualizar logs do sistema', 'Administração', 88),
        ]
        
        for nome, descricao, categoria, ordem in modulos:
            cursor.execute("SELECT id FROM modulos_sistema WHERE nome = ?", (nome,))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO modulos_sistema (nome, descricao, categoria, ordem, ativo)
                    VALUES (?, ?, ?, ?, 1)
                ''', (nome, descricao, categoria, ordem))
                logger.info(f"Módulo '{nome}' inserido no sistema.")
        
        # Permissões de Usuários
        if not table_exists("permissoes_usuarios"):
            cursor.execute('''
                CREATE TABLE permissoes_usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    modulo_id INTEGER NOT NULL,
                    concedido INTEGER DEFAULT 1,
                    concedido_por INTEGER,
                    concedido_em TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    FOREIGN KEY (modulo_id) REFERENCES modulos_sistema(id) ON DELETE CASCADE,
                    FOREIGN KEY (concedido_por) REFERENCES usuarios(id) ON DELETE SET NULL,
                    UNIQUE(usuario_id, modulo_id)
                )
            ''')
            logger.info("Tabela 'permissoes_usuarios' criada no SQLite.")
        else:
            logger.info("Tabela 'permissoes_usuarios' já existe.")

        # Perfis de Permissão
        if not table_exists("perfis_permissao"):
            cursor.execute('''
                CREATE TABLE perfis_permissao (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    descricao TEXT,
                    criado_por INTEGER,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (criado_por) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            ''')
            logger.info("Tabela 'perfis_permissao' criada no SQLite.")
        else:
            logger.info("Tabela 'perfis_permissao' já existe.")

        # Permissões por Perfil
        if not table_exists("perfis_permissao_modulos"):
            cursor.execute('''
                CREATE TABLE perfis_permissao_modulos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    perfil_id INTEGER NOT NULL,
                    modulo_id INTEGER NOT NULL,
                    FOREIGN KEY (perfil_id) REFERENCES perfis_permissao(id) ON DELETE CASCADE,
                    FOREIGN KEY (modulo_id) REFERENCES modulos_sistema(id) ON DELETE CASCADE,
                    UNIQUE(perfil_id, modulo_id)
                )
            ''')
            logger.info("Tabela 'perfis_permissao_modulos' criada no SQLite.")
        else:
            logger.info("Tabela 'perfis_permissao_modulos' já existe.")

        # Vínculo de Usuário com Perfil
        if not table_exists("usuario_perfil"):
            cursor.execute('''
                CREATE TABLE usuario_perfil (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL UNIQUE,
                    perfil_id INTEGER NOT NULL,
                    atribuido_por INTEGER,
                    atribuido_em TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
                    FOREIGN KEY (perfil_id) REFERENCES perfis_permissao(id) ON DELETE CASCADE,
                    FOREIGN KEY (atribuido_por) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            ''')
            logger.info("Tabela 'usuario_perfil' criada no SQLite.")
        else:
            logger.info("Tabela 'usuario_perfil' já existe.")

        # Migração: Inserir módulos que possam ter sido adicionados após criação inicial
        novos_modulos = [
            ('processos_imprimir', 'Imprimir lista de processos', 'Processos', 8),
            ('processos_pdf', 'Gerar PDF de processos', 'Processos', 9),
            ('processos_relatorio', 'Gerar relatórios de processos', 'Processos', 10),
            ('titulares_exportar', 'Exportar titulares para Excel', 'Titulares', 24),
            ('titulares_imprimir', 'Imprimir lista de titulares', 'Titulares', 25),
            ('atividades_visualizar', 'Visualizar histórico de atividades', 'Atividades', 30),
            ('atividades_exportar', 'Exportar log de atividades', 'Atividades', 31),
            ('metricas_visualizar', 'Visualizar métricas e dashboards', 'Métricas', 40),
            ('relatorios_geral', 'Acessar relatórios gerais', 'Métricas', 41),
            ('relatorios_exportar', 'Exportar relatórios', 'Métricas', 42),
            ('config_geral', 'Acessar configurações gerais do sistema', 'Configurações', 50),
            ('config_status', 'Gerenciar status de processos', 'Configurações', 51),
            ('config_tipos_servicos', 'Gerenciar tipos de serviço', 'Configurações', 52),
            ('config_email', 'Configurar e-mail do sistema', 'Configurações', 53),
            ('config_empresa', 'Editar dados da empresa', 'Configurações', 54),
            ('backup_visualizar', 'Visualizar página de backup', 'Backup', 60),
            ('backup_criar', 'Criar backups manuais', 'Backup', 61),
            ('backup_download', 'Baixar arquivos de backup', 'Backup', 62),
            ('backup_excluir', 'Excluir arquivos de backup', 'Backup', 63),
            ('backup_config', 'Configurar backup automático', 'Backup', 64),
            ('empresa_visualizar', 'Visualizar dados da empresa', 'Empresa', 70),
            ('empresa_editar', 'Editar dados da empresa', 'Empresa', 71),
            ('admin_usuarios_visualizar', 'Visualizar lista de usuários', 'Administração', 80),
            ('admin_usuarios_criar', 'Criar novos usuários', 'Administração', 81),
            ('admin_usuarios_editar', 'Editar dados de usuários', 'Administração', 82),
            ('admin_usuarios_excluir', 'Excluir usuários', 'Administração', 83),
            ('admin_usuarios_ativar', 'Ativar/desativar usuários', 'Administração', 84),
            ('admin_usuarios_senha', 'Resetar senha de usuários', 'Administração', 85),
            ('admin_permissoes', 'Gerenciar permissões de usuários', 'Administração', 86),
            ('admin_perfis', 'Gerenciar perfis de permissão', 'Administração', 87),
            ('admin_logs', 'Visualizar logs do sistema', 'Administração', 88),
        ]
        for nome, descricao, categoria, ordem in novos_modulos:
            cursor.execute('''
                INSERT OR IGNORE INTO modulos_sistema (nome, descricao, categoria, ordem, ativo)
                VALUES (?, ?, ?, ?, 1)
            ''', (nome, descricao, categoria, ordem))
        
        # ============================================
        # TABELAS DE AUDITORIA E SEGURANÇA - v3.16.5
        # ============================================

        # Auditoria administrativa
        if not table_exists("auditoria_admin"):
            cursor.execute("""
                CREATE TABLE auditoria_admin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    admin_nome TEXT,
                    admin_email TEXT,
                    acao TEXT NOT NULL,
                    usuario_afetado_id INTEGER,
                    usuario_afetado_nome TEXT,
                    usuario_afetado_email TEXT,
                    campo_alterado TEXT,
                    valor_anterior TEXT,
                    valor_novo TEXT,
                    justificativa TEXT,
                    ip TEXT,
                    user_agent TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (admin_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                    FOREIGN KEY (usuario_afetado_id) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            """)
            logger.info("Tabela 'auditoria_admin' criada no SQLite.")
        else:
            logger.info("Tabela 'auditoria_admin' já existe.")

        # Tentativas de acesso não autorizado
        if not table_exists("tentativas_acesso_nao_autorizado"):
            cursor.execute("""
                CREATE TABLE tentativas_acesso_nao_autorizado (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER,
                    usuario_nome TEXT,
                    tipo_tentativa TEXT NOT NULL,
                    detalhes TEXT,
                    alvo_user_id INTEGER,
                    alvo_user_nome TEXT,
                    ip TEXT,
                    user_agent TEXT,
                    bloqueado INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                    FOREIGN KEY (alvo_user_id) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            """)
            logger.info("Tabela 'tentativas_acesso_nao_autorizado' criada no SQLite.")
        else:
            logger.info("Tabela 'tentativas_acesso_nao_autorizado' já existe.")

        # Notificações de usuário (tabela separada para notificações internas de admin)
        if not table_exists("notificacoes_usuario"):
            cursor.execute("""
                CREATE TABLE notificacoes_usuario (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    mensagem TEXT NOT NULL,
                    acao_url TEXT,
                    lida INTEGER DEFAULT 0,
                    lida_em TEXT,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
                )
            """)
            logger.info("Tabela 'notificacoes_usuario' criada no SQLite.")
        else:
            logger.info("Tabela 'notificacoes_usuario' já existe.")

        # Criar índices de performance
        criar_indices_performance(cursor)
        
        # Inicializar FTS5 para busca full-text
        init_fts(cursor, conn)
        
        conn.commit()
