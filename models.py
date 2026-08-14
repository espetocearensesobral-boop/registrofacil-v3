# registrofacil/models.py

import os
from datetime import datetime, timedelta
import math
import re
import uuid
import base64
import sqlite3
from contextlib import contextmanager
import pytz 
import secrets

from config import Config 
from utils.logger import logger, security_logger
from utils.helpers import validarCPF, validarCNPJ, validar_telefone, validar_email

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

DATABASE_PATH = Config.DATABASE_PATH
TENTATIVAS_MAX = Config.TENTATIVAS_MAX
BLOQUEIO_TEMPO = Config.BLOQUEIO_TEMPO

def get_upload_folder():
    """Retorna o diretório de uploads de processos definido pelo Config.
    
    IMPORTANTE: o caminho é determinado exclusivamente por Config.UPLOAD_PROCESSOS_DIR,
    que aponta para static/uploads/processos no modo .py (dev) e para
    DATA_DIR/uploads/processos no modo .exe (frozen). Não usamos mais o campo
    uploads_path do banco de dados para routing de arquivos — ele gerava
    inconsistências quando configurado manualmente para um caminho diferente
    do usado por EMPRESA_UPLOAD_FOLDER e PROFILE_UPLOAD_FOLDER.
    """
    os.makedirs(Config.UPLOAD_PROCESSOS_DIR, exist_ok=True)
    return Config.UPLOAD_PROCESSOS_DIR

UPLOAD_FOLDER = Config.UPLOAD_PROCESSOS_DIR  # Mantido para compatibilidade

MAX_FILE_SIZE = Config.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS

LOCK_TIMEOUT_MINUTES = 15

_fernet_key = None
try:
    _fernet_key = Config.ENCRYPTION_KEY.encode('utf-8')
    f = Fernet(_fernet_key)
    logger.info("Fernet inicializado com ENCRYPTION_KEY do Config.")
except Exception as e:
    logger.critical(f"ERRO FATAL DE SEGURANÇA: Erro ao inicializar Fernet com ENCRYPTION_KEY do Config: {e}. A aplicação não pode continuar sem uma chave de criptografia válida.", exc_info=True)
    # Em produção, a aplicação deve falhar se a chave de segurança não for válida
    raise RuntimeError("Chave de criptografia inválida ou ausente. Verifique a configuração ENCRYPTION_KEY.")


def encrypt(data):
    if data is None:
        return None
    try:
        return f.encrypt(data.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao criptografar dados: {e}", exc_info=True)
        return None

def decrypt(data):
    if data is None:
        return None
    try:
        return f.decrypt(data.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao descriptografar dados: {e}. Dados podem estar corrompidos ou chave incorreta. Retornando None.", exc_info=True)
        return None

def validar_formato_matricula(matricula, processo_id=None):
    """
    Validação de matrícula: apenas formato, sem unicidade.
    Matrícula é opcional — se vazia/None, retorna True sem validar.

    Nota: 'processo_id' é aceito por compatibilidade de assinatura com os
    chamadores, mas não é usado aqui (não há checagem de duplicidade nesta
    função — apenas formato via regex).
    """
    if not matricula:
        return True  # Matrícula é opcional
    if not re.fullmatch(r'^[A-Za-z0-9\s\-\.\/]{1,50}$', matricula):
        raise ValueError("Matrícula inválida. Use apenas letras, números, espaços, hífens, pontos e barras (1-50 caracteres).")
    return True

def validar_telefone_unico(telefone, processo_id=None, titular_id=None, titular_nome=None):
    if not telefone: return True
    
    # Verificar em processos (apresentante_telefone)
    query_proc = "SELECT id FROM processos WHERE apresentante_telefone = ?"
    params_proc = [telefone]
    if processo_id:
        query_proc += " AND id != ?"
        params_proc.append(processo_id)
    
    # Se o titular_nome for fornecido, ignoramos processos do mesmo titular
    if titular_nome:
        query_proc += " AND titular != ?"
        params_proc.append(titular_nome)
    
    try:
        if executar_query(query_proc, params_proc, fetch_one=True):
            raise ValueError(f"TELEFONE: O telefone '{telefone}' já existe no sistema em outro processo de um titular diferente.")
            
        # Verificar em titulares
        query_tit = "SELECT id FROM titulares WHERE telefone = ?"
        params_tit = [telefone]
        
        # Se titular_nome for fornecido, tentamos achar o ID dele para ignorar na busca de duplicidade
        if titular_nome and not titular_id:
            tit_info = executar_query("SELECT id FROM titulares WHERE nome = ?", [titular_nome], fetch_one=True)
            if tit_info:
                titular_id = tit_info['id']

        # Se estamos editando um processo, precisamos encontrar se o titular vinculado a ele
        # é o mesmo que possui este telefone, para não dar falso positivo.
        titular_vinculado_id = None
        if processo_id:
            try:
                proc = executar_query("SELECT titular FROM processos WHERE id = ?", [processo_id], fetch_one=True)
                if proc:
                    tit = executar_query("SELECT id FROM titulares WHERE nome = ?", [proc['titular']], fetch_one=True)
                    if tit:
                        titular_vinculado_id = tit['id']
            except Exception as e:
                logger.error(f"Erro ao buscar titular vinculado para validação de telefone: {e}")

        target_titular_id = titular_id or titular_vinculado_id
        if target_titular_id:
            query_tit += " AND id != ?"
            params_tit.append(target_titular_id)
            
        if executar_query(query_tit, params_tit, fetch_one=True):
            raise ValueError(f"TELEFONE: O telefone '{telefone}' já existe no sistema vinculado a outro titular.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao validar telefone único: {e}")
        raise ValueError("Erro ao validar telefone no banco de dados.")
    return True

def validar_email_unico(email, processo_id=None, titular_id=None, titular_nome=None):
    if not email: return True
    
    # Verificar em processos (apresentante_email)
    query_proc = "SELECT id FROM processos WHERE apresentante_email = ?"
    params_proc = [email]
    if processo_id:
        query_proc += " AND id != ?"
        params_proc.append(processo_id)
    
    # Se o titular_nome for fornecido, ignoramos processos do mesmo titular
    if titular_nome:
        query_proc += " AND titular != ?"
        params_proc.append(titular_nome)
        
    try:
        if executar_query(query_proc, params_proc, fetch_one=True):
            raise ValueError(f"E-MAIL: O e-mail '{email}' já existe no sistema em outro processo de um titular diferente.")
            
        # Verificar em titulares
        query_tit = "SELECT id FROM titulares WHERE email = ?"
        params_tit = [email]
        
        # Se titular_nome for fornecido, tentamos achar o ID dele para ignorar na busca de duplicidade
        if titular_nome and not titular_id:
            tit_info = executar_query("SELECT id FROM titulares WHERE nome = ?", [titular_nome], fetch_one=True)
            if tit_info:
                titular_id = tit_info['id']

        # Se estamos editando um processo, precisamos encontrar se o titular vinculado a ele
        # é o mesmo que possui este e-mail, para não dar falso positivo.
        titular_vinculado_id = None
        if processo_id:
            try:
                proc = executar_query("SELECT titular FROM processos WHERE id = ?", [processo_id], fetch_one=True)
                if proc:
                    tit = executar_query("SELECT id FROM titulares WHERE nome = ?", [proc['titular']], fetch_one=True)
                    if tit:
                        titular_vinculado_id = tit['id']
            except Exception as e:
                logger.error(f"Erro ao buscar titular vinculado para validação de e-mail: {e}")

        target_titular_id = titular_id or titular_vinculado_id
        if target_titular_id:
            query_tit += " AND id != ?"
            params_tit.append(target_titular_id)
            
        if executar_query(query_tit, params_tit, fetch_one=True):
            raise ValueError(f"E-MAIL: O e-mail '{email}' já existe no sistema vinculado a outro titular.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao validar e-mail único: {e}")
        raise ValueError("Erro ao validar e-mail no banco de dados.")
    return True

def validar_tipo_servico(tipo_id):
    if not isinstance(tipo_id, int) or tipo_id <= 0:
        raise ValueError("ID de tipo de serviço inválido.")
    result = executar_query("SELECT id FROM tipos_servico WHERE id = ? AND ativo = 1", [tipo_id], fetch_one=True)
    if not result:
        raise ValueError(f"Tipo de serviço com ID {tipo_id} inválido, não encontrado ou inativo.")
    return True

def validar_status(status_nome):
    if not status_nome:
        raise ValueError("Nome do status não pode ser vazio.")
    result = executar_query("SELECT id FROM status_processo WHERE nome = ? AND ativo = 1", [status_nome], fetch_one=True)
    if not result:
        raise ValueError(f"Status '{status_nome}' inválido, não encontrado ou inativo.")
    return True

def validar_nome_unico_db(tabela, coluna, nome, id_excluir=None):
    query = f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} = ?"
    params = [nome]
    if id_excluir:
        query += " AND id != ?"
        params.append(id_excluir)
    
    result = executar_query(query, params, fetch_one=True)
    if result['COUNT(*)'] > 0:
        raise ValueError(f"O nome '{nome}' já está em uso.")
    return True

@contextmanager
def get_sqlite_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        # WAL (Write-Ahead Log) mode: muito mais resistente a corrupção no Windows
        # pois permite leituras simultâneas e não usa journal de rollback no mesmo arquivo.
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")  # Mais rápido que FULL, seguro com WAL
        conn.execute("PRAGMA busy_timeout=5000")   # Aguarda 5s se banco estiver bloqueado
        conn.execute("PRAGMA foreign_keys=ON")     # Ativa FK para ON DELETE SET NULL
        yield conn
        conn.commit()
    except sqlite3.DatabaseError as e:
        error_msg = str(e).lower()
        if 'malformed' in error_msg or 'corrupt' in error_msg or 'disk image' in error_msg:
            logger.critical(
                f"CORRUPÇÃO DETECTADA no banco de dados '{DATABASE_PATH}': {e}. "
                "Acesse Backup > Reparar BD para tentar recuperar o banco de dados.",
                exc_info=True
            )
        else:
            logger.critical(f"Erro ao conectar ou operar com SQLite: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    except sqlite3.Error as e:
        logger.critical(f"Erro ao conectar ou operar com SQLite: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


def executar_query(query, params=None, fetch_one=False, fetch_all=False, connection=None):
    if connection:
        conn = connection
        close_conn = False
    else:
        conn = sqlite3.connect(DATABASE_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        close_conn = True

    try:
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if query.strip().upper().startswith('SELECT'):
            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            else:
                results = cursor.fetchall()
                return [dict(row) for row in results]
        else:
            if close_conn:
                conn.commit()
            return cursor.rowcount
    except sqlite3.Error as e:
        logger.error(f"Erro no banco de dados SQLite ao executar query '{query}': {e}", exc_info=True)
        if close_conn:
            try:
                conn.rollback()
            except sqlite3.Error as rb_e:
                logger.error(f"Erro ao tentar rollback da conexão local: {rb_e}")
        raise
    finally:
        if close_conn:
            conn.close()

def add_column_if_not_exists_sqlite(table_name, column_name, column_type, default_value=None):
    """Adiciona coluna se não existir, com tratamento especial para funções SQL"""
    # Usar uma conexão separada para PRAGMA para evitar problemas de bloqueio
    # se a função for chamada dentro de uma transação.
    with get_sqlite_connection() as temp_conn:
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [info[1] for info in temp_cursor.fetchall()]

    if column_name not in columns:
        # Para funções SQL, usamos uma abordagem diferente
        if default_value and isinstance(default_value, str) and (
            default_value.startswith("strftime(") or
            default_value.upper() == 'CURRENT_TIMESTAMP' or
            default_value.upper() == 'CURRENT_DATE' or
            default_value.upper() == 'CURRENT_TIME'
        ):
            # Primeiro adicionamos a coluna sem DEFAULT
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            
            try:
                with get_sqlite_connection() as conn_for_alter:
                    cursor_for_alter = conn_for_alter.cursor()
                    cursor_for_alter.execute(alter_sql)
                    logger.info(f"Coluna '{column_name}' adicionada à tabela '{table_name}' sem valor padrão inicial.")
                    
                    # Depois atualizamos o valor padrão para registros existentes com a função SQL
                    # e definimos o valor padrão para futuras inserções (se a versão do SQLite permitir ALTER TABLE ADD COLUMN DEFAULT)
                    # NOTA: SQLite mais antigas não permitem ALTER TABLE ADD COLUMN com DEFAULT para valores não-constantes.
                    # A melhor abordagem para compatibilidade é atualizar os valores existentes via UPDATE e gerenciar o default na aplicação.
                    update_sql = f"UPDATE {table_name} SET {column_name} = {default_value} WHERE {column_name} IS NULL;"
                    cursor_for_alter.execute(update_sql)
                    logger.info(f"Valores existentes na coluna '{column_name}' da tabela '{table_name}' atualizados com '{default_value}'.")

            except sqlite3.OperationalError as e:
                logger.error(f"Erro operacional SQLite ao adicionar ou atualizar coluna '{column_name}' à tabela '{table_name}': {e}. SQL: {alter_sql}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Erro inesperado ao adicionar ou atualizar coluna '{column_name}' à tabela '{table_name}': {e}. SQL: {alter_sql}", exc_info=True)
                raise
        else:
            # Para valores normais (não funções SQL), procedemos como antes
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value is not None:
                # Para literais de texto normais, mantenha as aspas simples.
                if column_type.upper() == 'TEXT':
                    alter_sql += f" DEFAULT '{default_value}'"
                else:
                    # Para outros tipos (INTEGER, REAL, etc.), sem aspas.
                    alter_sql += f" DEFAULT {default_value}"
            
            try:
                with get_sqlite_connection() as conn_for_alter:
                    cursor_for_alter = conn_for_alter.cursor()
                    cursor_for_alter.execute(alter_sql)
                    logger.info(f"Coluna '{column_name}' adicionada à tabela '{table_name}' com valor padrão.")
            except sqlite3.OperationalError as e:
                logger.error(f"Erro operacional SQLite ao adicionar coluna '{column_name}' à tabela '{table_name}': {e}. SQL: {alter_sql}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Erro inesperado ao adicionar coluna '{column_name}' à tabela '{table_name}': {e}. SQL: {alter_sql}", exc_info=True)
                raise



def executar_migracoes_dados(connection=None):
    """
    Sistema de migrações versionadas de dados.
    Usa PRAGMA user_version para controlar quais migrações já foram aplicadas.
    Cada migração tem um número sequencial e é aplicada apenas uma vez.
    """
    def get_conn():
        return connection if connection else get_sqlite_connection().__enter__()

    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version")
        versao_atual = cursor.fetchone()[0]
        logger.info(f"Versão atual do banco (user_version): {versao_atual}")

        migracoes = []

        # -------------------------------------------------------
        # Migração 1: Corrigir possui_matricula NULL → 1 em
        # processos que já tinham matrícula preenchida
        # -------------------------------------------------------
        def migracao_001(cursor):
            cursor.execute("""
                UPDATE processos
                SET possui_matricula = 1
                WHERE matricula IS NOT NULL
                  AND matricula != ''
                  AND (possui_matricula IS NULL OR possui_matricula = 0)
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 001] {n} processo(s) tiveram possui_matricula corrigido para 1.")

        migracoes.append(migracao_001)

        # -------------------------------------------------------
        # Migração 2: Sincronizar ultimo_registro_id em titulares
        # para apontar para o processo mais recente de cada titular
        # -------------------------------------------------------
        def migracao_002(cursor):
            cursor.execute("""
                UPDATE titulares
                SET ultimo_registro_id = (
                    SELECT p.id FROM processos p
                    WHERE p.titular = titulares.nome
                    ORDER BY p.data_entrada DESC, p.id DESC
                    LIMIT 1
                )
                WHERE (
                    ultimo_registro_id IS NULL
                    OR NOT EXISTS (
                        SELECT 1 FROM processos WHERE id = titulares.ultimo_registro_id
                    )
                )
                AND EXISTS (
                    SELECT 1 FROM processos WHERE titular = titulares.nome
                )
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 002] {n} titular(es) tiveram ultimo_registro_id sincronizado.")

        migracoes.append(migracao_002)

        # -------------------------------------------------------
        # Migração 3: Preencher numero_processo NULL com valor
        # padrão baseado no ID para evitar falhas de unicidade
        # -------------------------------------------------------
        def migracao_003(cursor):
            cursor.execute("""
                UPDATE processos
                SET numero_processo = 'PROC-' || CAST(id AS TEXT)
                WHERE numero_processo IS NULL OR numero_processo = ''
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 003] {n} processo(s) receberam numero_processo padrão.")

        migracoes.append(migracao_003)

        # -------------------------------------------------------
        # Migração 4: Garantir envolvido_notas = 0 onde está NULL
        # -------------------------------------------------------
        def migracao_004(cursor):
            cursor.execute("""
                UPDATE processos SET envolvido_notas = 0
                WHERE envolvido_notas IS NULL
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 004] {n} processo(s) tiveram envolvido_notas normalizado.")

        migracoes.append(migracao_004)

        # -------------------------------------------------------
        # Migração 5: Normalizar must_change_password NULL → 0
        # -------------------------------------------------------
        def migracao_005(cursor):
            cursor.execute("""
                UPDATE usuarios SET must_change_password = 0
                WHERE must_change_password IS NULL
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 005] {n} usuário(s) tiveram must_change_password normalizado.")

        migracoes.append(migracao_005)

        # -------------------------------------------------------
        # Migração 6: Normalizar ativo = 1 onde está NULL em
        # tipos_servico e status_processo
        # -------------------------------------------------------
        def migracao_006(cursor):
            cursor.execute("UPDATE tipos_servico SET ativo = 1 WHERE ativo IS NULL")
            n1 = cursor.rowcount
            cursor.execute("UPDATE status_processo SET ativo = 1 WHERE ativo IS NULL")
            n2 = cursor.rowcount
            if n1 + n2 > 0:
                logger.info(f"[Migração 006] {n1} tipo(s) e {n2} status normalizados (ativo = 1).")

        migracoes.append(migracao_006)

        # -------------------------------------------------------
        # Aplicar apenas as migrações pendentes
        # -------------------------------------------------------
        total = len(migracoes)
        pendentes = migracoes[versao_atual:]

        if not pendentes:
            logger.info("Banco de dados já está na versão mais recente. Nenhuma migração necessária.")
            return

        logger.info(f"Aplicando {len(pendentes)} migração(ões) (v{versao_atual} → v{total})...")

        try:
            for i, migracao in enumerate(pendentes, start=versao_atual + 1):
                logger.info(f"Executando migração {i:03d}...")
                migracao(cursor)

            cursor.execute(f"PRAGMA user_version = {total}")
            conn.commit()
            logger.info(f"Migrações concluídas. Banco atualizado para versão {total}.")
        except Exception as e:
            conn.rollback()
            logger.error(f"Erro durante migrações de dados. Rollback efetuado. Erro: {e}", exc_info=True)
            raise


def init_db():
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
                    foto TEXT,
                    role TEXT DEFAULT 'user' NOT NULL,
                    created_at TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    updated_at TEXT,
                    deleted_at TEXT,
                    last_login_at TEXT,
                    session_invalidate_at TEXT, -- Adicionado diretamente na criação da tabela
                    must_change_password INTEGER DEFAULT 0 -- 1 = exige troca de senha no próximo login
                );
            """)
            logger.info("Tabela 'usuarios' criada no SQLite.")
        else:
            logger.info("Tabela 'usuarios' já existe. Verificando/adicionando colunas.")
            add_column_if_not_exists_sqlite('usuarios', 'foto', 'TEXT')
            add_column_if_not_exists_sqlite('usuarios', 'updated_at', 'TEXT', default_value="strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
            add_column_if_not_exists_sqlite('usuarios', 'deleted_at', 'TEXT')
            add_column_if_not_exists_sqlite('usuarios', 'role', "TEXT DEFAULT 'user' NOT NULL")
            add_column_if_not_exists_sqlite('usuarios', 'last_login_at', 'TEXT')
            # Mantido aqui como fallback para bases de dados mais antigas que já existiam antes da mudança no CREATE TABLE
            add_column_if_not_exists_sqlite('usuarios', 'session_invalidate_at', 'TEXT')
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
                senha_hash = generate_password_hash('admin123')
                cursor.execute(
                    "INSERT INTO usuarios (nome, email, usuario, senha, ativo, role, must_change_password, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))",
                    ['Administrador', 'admin@exemplo.com', 'admin', senha_hash, 1, 'admin', 1]
                )
                logger.info("Usuário padrão 'admin / admin123' criado. Troca de senha obrigatória no primeiro acesso.")
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
                    tema_cor TEXT DEFAULT 'dourado',
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
            add_column_if_not_exists_sqlite("user_preferences", "tema_cor", "TEXT", "dourado")

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

def gravar_log(acao, processo_id=None, usuario_id=None, ip=None, descricao=None, contexto=None, connection=None):
    """
    Grava um log de atividade.
    - acao:      tipo da ação (ex: "Editou processo")
    - descricao: descrição principal — combinada com acao para exibição na tabela
                 (ex: "Processo: Titular (Matrícula: x)")
                 A coluna 'acao' no banco armazenará "Editou processo: Processo: Titular (Matrícula: x)"
    - contexto:  detalhes extras exibidos APENAS no modal de detalhe
                 (ex: "Status alterado de 'A' para 'B'\nCampo X: antigo → novo")
    Ações de segurança/acesso são gravadas em arquivo de texto.
    Ações de auditoria de processos são gravadas no banco de dados.
    """

    # Lista de ações de correspondência EXATA que devem ir para o arquivo de texto
    LOG_TO_FILE_ACTIONS = {
        'Logout do sistema', 'Link de recuperação de senha enviado',
        'Novo usuário registrado', 'Editou usuário', 'Inativou usuário',
        'Imprimiu lista de processos'
    }
    # Lista de PREFIXOS de ações que também devem ir para o arquivo de texto
    LOG_TO_FILE_PREFIXES = (
        'Login bem-sucedido',
        'Falha de login:',
        'Falha de cadastro:',
        'Erro durante login:',
        'Tentativa de login bloqueada',
        'Exportou'
    )

    # Ações que não devem ser registradas para evitar poluição
    ACOES_IGNORADAS = {
        'pesquisa_realizada', 'acquire_lock', 'renew_lock', 'release_lock',
        'acquire_lock_falha', 'renew_lock_falha', 'release_lock_falha'
    }

    if acao in ACOES_IGNORADAS:
        return  # Ignora o log silenciosamente

    # Prefixos permitidos para gravação no banco de dados.
    # Somente ações de Cadastro, Edição e Exclusão são registradas.
    PREFIXOS_BANCO = ('Cadastrou', 'Editou', 'Exclu')

    # Ações exatas adicionais que também devem ser gravadas no banco.
    ACOES_BANCO_EXATAS = {
        'Backup Manual',
        'Backup Automático',
        'Backup Automático SFTP',
        'Otimizou banco de dados',
        'Configurações de e-mail atualizadas',
    }

    log_para_arquivo = acao in LOG_TO_FILE_ACTIONS or acao.startswith(LOG_TO_FILE_PREFIXES)

    if log_para_arquivo:
        # Formata a mensagem para o arquivo de texto
        user_info = f"Usuário ID: {usuario_id if usuario_id else 'N/A'}"
        ip_info = f"IP: {ip if ip else 'N/A'}"
        detalhes = f"Detalhes: {descricao}" if descricao else f"Ação: {acao}"
        id_processo_info = f"Processo ID: {processo_id}" if processo_id else ""
        log_message = f"[{user_info}] [{ip_info}] - {detalhes} {id_processo_info}".strip()
        security_logger.info(log_message)

    elif acao.startswith(PREFIXOS_BANCO) or acao in ACOES_BANCO_EXATAS:
        # Somente ações de Cadastro, Edição e Exclusão são gravadas no banco.
        # 'acao' na tabela = "Tipo: Descrição principal" (formato original visível na listagem)
        # 'contexto' = detalhes extras exibidos apenas no modal
        final_acao = acao if descricao is None else f"{acao}: {descricao}"
        try:
            # Usa o usuario_id diretamente (passado pela sessão, sempre válido)
            safe_usuario_id = usuario_id

            # Valida processo_id
            safe_processo_id = None
            if processo_id is not None:
                try:
                    proc_exists = executar_query(
                        "SELECT 1 FROM processos WHERE id = ?", [processo_id], fetch_one=True
                    )
                    safe_processo_id = processo_id if proc_exists else None
                except Exception:
                    safe_processo_id = None

            executar_query(
                "INSERT INTO logs (acao, contexto, processo_id, usuario_id, ip, timestamp) "
                "VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))",
                [final_acao, contexto, safe_processo_id, safe_usuario_id, ip],
                connection=connection
            )
        except Exception as e:
            logger.error(f"Falha ao gravar log no BANCO DE DADOS para ação '{final_acao}': {e}", exc_info=True)

def verificar_tentativas_login(ip):
    tempo_limite = datetime.now() - timedelta(seconds=BLOQUEIO_TEMPO)
    tempo_limite_str = tempo_limite.strftime('%Y-%m-%d %H:%M:%S')

    result = executar_query(
        "SELECT COUNT(*) AS total_count FROM login_attempts WHERE ip = ? AND tempo > ? AND sucesso = 0",
        [ip, tempo_limite_str], fetch_one=True
    )
    if result and result['total_count'] >= TENTATIVAS_MAX:
        logger.warning(f"IP '{ip}' bloqueado por excesso de tentativas de login ({result['total_count']} falhas).")
        return False, f"Muitas tentativas de login. Tente novamente em {BLOQUEIO_TEMPO // 60} minutos."
    return True, None

def registrar_tentativa_login(ip, sucesso):
    return executar_query(
        "INSERT INTO login_attempts (ip, sucesso, tempo) VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))",
        [ip, 1 if sucesso else 0]
    )

def get_user_by_username(username):
    # Solução Completa (Recomendada) para lidar com a coluna session_invalidate_at
    try:
        # CORREÇÃO DE IMAGEM/CACHE: Adicionando updated_at na query para o cache-busting
        return executar_query(
            "SELECT id, nome, email, usuario, senha, ativo, foto, role, "
            "created_at, updated_at, deleted_at, last_login_at, session_invalidate_at "
            "FROM usuarios WHERE usuario = ?",
            [username],
            fetch_one=True
        )
    except sqlite3.OperationalError as e:
        if "no such column: session_invalidate_at" in str(e):
            # Se a coluna não existe, retorna sem ela e loga um aviso
            logger.warning(f"Coluna 'session_invalidate_at' não encontrada durante a inicialização/migração. Selecionando usuário sem ela. Erro: {e}")
            return executar_query(
                "SELECT id, nome, email, usuario, senha, ativo, foto, role, "
                "created_at, updated_at, deleted_at, last_login_at "
                "FROM usuarios WHERE usuario = ?",
                [username],
                fetch_one=True
            )
        raise # Re-lança outros erros de OperationalError

def update_user_last_login(user_id):
    fortaleza_tz = pytz.timezone('America/Fortaleza')
    now_fortaleza = datetime.now(fortaleza_tz)
    current_time_str = now_fortaleza.strftime('%Y-%m-%d %H:%M:%S')
    
    return executar_query(
        "UPDATE usuarios SET last_login_at = ?, updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?",
        [current_time_str, user_id]
    )

def create_user(nome, email, usuario, senha_hash, role='user'):
    """
    Cria um novo usuário no sistema e concede permissões básicas
    """
    try:
        # Inserir usuário no banco
        rows_affected = executar_query(
            "INSERT INTO usuarios (nome, email, usuario, senha, ativo, role, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))",
            [nome, email, usuario, senha_hash, 1, role]
        )
        
        if rows_affected:
            logger.info(f"Usuário '{usuario}' criado com sucesso no banco de dados com role '{role}'.")
            
            # Conceder permissões básicas automaticamente
            try:
                # Buscar ID do usuário recém-criado
                user_query = "SELECT id FROM usuarios WHERE usuario = ? ORDER BY id DESC LIMIT 1"
                novo_usuario = executar_query(user_query, [usuario], fetch_one=True)
                
                if novo_usuario:
                    novo_usuario_id = novo_usuario['id']
                    
                    # Se não for admin, NÃO conceder permissões automáticas.
                    # Um admin deve atribuir um perfil ou permissões manualmente.
                    if role not in ['admin', 'suporte']:
                        logger.info(f"Usuário '{usuario}' (ID: {novo_usuario_id}) criado sem permissões. "
                                    f"Um admin deve atribuir permissões ou um perfil.")
                    else:
                        # Para admins, conceder todas as permissões
                        modulos_query = "SELECT id FROM modulos_sistema WHERE ativo = 1"
                        modulos = executar_query(modulos_query)
                        
                        if modulos:
                            for modulo in modulos:
                                perm_query = """
                                    INSERT OR IGNORE INTO permissoes_usuarios (usuario_id, modulo_id, concedido, concedido_por)
                                    VALUES (?, ?, 1, ?)
                                """
                                executar_query(perm_query, [novo_usuario_id, modulo['id'], novo_usuario_id])
                            
                            logger.info(f"Todas as permissões concedidas ao admin '{usuario}' (ID: {novo_usuario_id})")
                        
            except Exception as e:
                # Não bloquear a criação do usuário se houver erro nas permissões
                logger.warning(f"Erro ao conceder permissões ao novo usuário '{usuario}': {e}")
            
        return rows_affected
        
    except sqlite3.IntegrityError as e:
        logger.warning(f"Tentativa de criar usuário com email '{email}' ou usuario '{usuario}' já existente. Erro: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao criar novo usuário: {e}", exc_info=True)
        return None

def get_config(key):
    result = executar_query("SELECT valor FROM configuracoes WHERE chave = ?", [key], fetch_one=True)
    return result['valor'] if result else None

def set_config(key, value):
    try:
        rows_affected = executar_query("UPDATE configuracoes SET valor = ?, updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE chave = ?", [value, key])
        if rows_affected == 0:
            executar_query("INSERT INTO configuracoes (chave, valor, updated_at) VALUES (?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))", [key, value])
        logger.info(f"Configuração '{key}' definida/atualizada para '{value}'.")
        return True
    except Exception as e:
        logger.error(f"Erro ao definir/atualizar configuração '{key}': {e}", exc_info=True)
        return False


def obter_tipos_servico():
    return executar_query("SELECT id, nome, descricao, ativo, prazo_padrao FROM tipos_servico ORDER BY nome ASC")

def obter_status_processo_config():
    return executar_query("""
        SELECT sp.id, sp.nome, sp.hex_color, sp.ativo, 
        (SELECT COUNT(*) FROM processos p WHERE p.status_id = sp.id) as total_processos
        FROM status_processo sp 
        ORDER BY sp.nome ASC
    """)

def get_status_id_by_name(status_name):
    result = executar_query("SELECT id FROM status_processo WHERE nome = ?", [status_name], fetch_one=True)
    return result['id'] if result else None

def obter_usuarios_para_selecao():
    return executar_query("SELECT id, nome FROM usuarios WHERE ativo = 1 ORDER BY nome ASC")

def create_processo(numero_processo, titular, titular_telefone, titular_email, matricula, tipo_id, data_entrada, status_id, prazo_final, apresentante, apresentante_telefone, apresentante_email, responsavel_id, envolvido_notas, observacoes, data_conclusao, possui_matricula=0, connection=None, titular_id=None, apresentante_id=None):
    try:
        query = """
            INSERT INTO processos (numero_processo, titular, titular_id, titular_telefone, titular_email, matricula, possui_matricula, tipo_id, data_entrada, status_id,
                                   prazo_final, apresentante, apresentante_id, apresentante_telefone, apresentante_email,
                                   responsavel_id, envolvido_notas, observacoes, data_conclusao,
                                   created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """
        formatted_data_entrada = data_entrada
        formatted_prazo_final = prazo_final
        formatted_data_conclusao = data_conclusao
        # Se não possui matrícula, garantir que o valor seja NULL
        matricula_final = matricula if possui_matricula else None

        params = [
            numero_processo, titular, titular_id, titular_telefone, titular_email, matricula_final, possui_matricula, tipo_id, formatted_data_entrada, status_id,
            formatted_prazo_final, apresentante, apresentante_id, apresentante_telefone, apresentante_email,
            responsavel_id, envolvido_notas, observacoes, formatted_data_conclusao
        ]
        
        cursor = connection.cursor()
        cursor.execute(query, params)
        processo_id = cursor.lastrowid
        
        registrar_historico_processo(
            processo_id=processo_id,
            usuario_id=responsavel_id,
            campo_alterado='criacao',
            valor_antigo=None,
            valor_novo=f"Processo criado: {titular}",
            observacao_adicional=f"Processo ID {processo_id} criado.",
            connection=connection
        )
        
        logger.info(f"Processo '{numero_processo}' criado com sucesso no DB com ID: {processo_id}.")
        return processo_id
    except sqlite3.IntegrityError as e:
        logger.warning(f"Tentativa de criar processo com número '{numero_processo}' já existente. Erro: {e}")
        raise ValueError("Erro de integridade ao criar processo.") from e
    except Exception as e:
        logger.error(f"Erro ao criar processo '{numero_processo}': {e}", exc_info=True)
        raise

def get_processo_by_id(processo_id):
    query = """
        SELECT
            P.id, P.numero_processo, P.titular, P.titular_id, P.titular_telefone, P.titular_email, P.matricula, P.possui_matricula, P.tipo_id,
            P.data_entrada, P.status_id, P.prazo_final, P.apresentante, P.apresentante_id,
            P.apresentante_telefone, P.apresentante_email, P.responsavel_id,
            P.envolvido_notas, P.observacoes, P.data_conclusao, P.created_at, P.updated_at,
            TS.nome AS tipo_nome, TS.prazo_padrao, SP.nome AS status_nome_original, SP.hex_color AS status_hex_original,
            U.nome AS responsavel_nome
        FROM processos P
        JOIN tipos_servico TS ON P.tipo_id = TS.id
        JOIN status_processo SP ON P.status_id = SP.id
        LEFT JOIN usuarios U ON P.responsavel_id = U.id
        WHERE P.id = ?
    """
    return executar_query(query, [processo_id], fetch_one=True)

def update_processo(processo_id, titular, titular_telefone, titular_email, matricula, tipo_id, data_entrada, status_id, prazo_final, apresentante, apresentante_telefone, apresentante_email, responsavel_id, envolvido_notas, observacoes, data_conclusao, possui_matricula=0, connection=None, titular_id=None, apresentante_id=None):
    try:
        old_processo_data = get_processo_by_id(processo_id)
        if not old_processo_data:
            raise ValueError(f"Processo com ID {processo_id} não encontrado para atualização.")

        formatted_data_entrada = data_entrada
        formatted_prazo_final = prazo_final
        formatted_data_conclusao = data_conclusao
        # Se não possui matrícula, garantir que o valor seja NULL
        matricula_final = matricula if possui_matricula else None

        query = """
            UPDATE processos SET
            titular = ?, titular_id = ?, titular_telefone = ?, titular_email = ?, matricula = ?, possui_matricula = ?, tipo_id = ?, data_entrada = ?, status_id = ?,
            prazo_final = ?, apresentante = ?, apresentante_id = ?, apresentante_telefone = ?, apresentante_email = ?,
            responsavel_id = ?, envolvido_notas = ?, observacoes = ?, data_conclusao = ?,
            updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
            WHERE id = ?
        """
        params = [
            titular, titular_id, titular_telefone, titular_email, matricula_final, possui_matricula, tipo_id, formatted_data_entrada, status_id,
            formatted_prazo_final, apresentante, apresentante_id, apresentante_telefone, apresentante_email,
            responsavel_id, envolvido_notas, observacoes, formatted_data_conclusao,
            processo_id
        ]

        cursor = connection.cursor()

        # Tentativa 1: UPDATE normal (trigger FTS dispara automaticamente)
        try:
            cursor.execute(query, params)
        except sqlite3.DatabaseError as db_err:
            err_msg = str(db_err).lower()
            # Se o erro vier do trigger FTS (malformed/corrupt), reconstruir FTS e tentar novamente
            if 'malformed' in err_msg or 'corrupt' in err_msg or 'disk image' in err_msg:
                logger.warning(
                    f"FTS5 corrompido detectado durante update_processo({processo_id}). "
                    "Reconstruindo índice FTS e tentando novamente..."
                )
                # Commit parcial para liberar a transação travada
                try:
                    connection.rollback()
                except Exception:
                    pass

                # Reconstruir FTS usando nova conexão independente
                try:
                    rebuild_fts_index()
                    logger.info("FTS5 reconstruído com sucesso. Tentando UPDATE novamente.")
                except Exception as rebuild_err:
                    logger.error(f"Falha ao reconstruir FTS5: {rebuild_err}")

                # Tentativa 2: UPDATE sem trigger (drop trigger temporariamente)
                try:
                    cursor2 = connection.cursor()
                    # Desabilitar triggers FTS temporariamente para este UPDATE
                    cursor2.execute("DROP TRIGGER IF EXISTS processos_fts_update")
                    cursor2.execute(query, params)
                    logger.info(f"UPDATE do processo {processo_id} concluído sem trigger FTS.")
                    # Recriar o trigger correto
                    cursor2.execute("""
                        CREATE TRIGGER IF NOT EXISTS processos_fts_update
                        AFTER UPDATE ON processos BEGIN
                            DELETE FROM processos_fts WHERE rowid = old.id;
                            INSERT INTO processos_fts(rowid, numero_processo, titular, matricula, apresentante, observacoes)
                            VALUES (new.id, new.numero_processo, new.titular, new.matricula, new.apresentante, new.observacoes);
                        END
                    """)
                    cursor = cursor2
                except Exception as retry_err:
                    logger.error(f"Tentativa 2 de UPDATE também falhou: {retry_err}")
                    raise sqlite3.DatabaseError(
                        f"Falha persistente ao salvar processo mesmo após reconstrução do FTS. "
                        f"Erro original: {db_err}. Erro na segunda tentativa: {retry_err}"
                    )
            else:
                raise
        rows_affected = cursor.rowcount

        if rows_affected:
            current_data = {
                'titular': titular,
                'matricula': matricula_final,
                'possui_matricula': possui_matricula,
                'tipo_id': tipo_id,
                'data_entrada': formatted_data_entrada,
                'status_id': status_id,
                'prazo_final': formatted_prazo_final,
                'apresentante': apresentante,
                'apresentante_telefone': apresentante_telefone,
                'apresentante_email': apresentante_email,
                'responsavel_id': responsavel_id,
                'envolvido_notas': envolvido_notas,
                'observacoes': observacoes,
                'data_conclusao': data_conclusao
            }
            tipo_nome_antigo = executar_query("SELECT nome FROM tipos_servico WHERE id = ?", [old_processo_data['tipo_id']], fetch_one=True, connection=connection)['nome'] if old_processo_data['tipo_id'] else None
            tipo_nome_novo = executar_query("SELECT nome FROM tipos_servico WHERE id = ?", [tipo_id], fetch_one=True, connection=connection)['nome'] if tipo_id else None

            status_nome_antigo = executar_query("SELECT nome FROM status_processo WHERE id = ?", [old_processo_data['status_id']], fetch_one=True, connection=connection)['nome'] if old_processo_data['status_id'] else None
            status_nome_novo = executar_query("SELECT nome FROM status_processo WHERE id = ?", [status_id], fetch_one=True, connection=connection)['nome'] if status_id else None
            
            responsavel_nome_antigo = executar_query("SELECT nome FROM usuarios WHERE id = ?", [old_processo_data['responsavel_id']], fetch_one=True, connection=connection)['nome'] if old_processo_data['responsavel_id'] else None
            responsavel_nome_novo = executar_query("SELECT nome FROM usuarios WHERE id = ?", [responsavel_id], fetch_one=True, connection=connection)['nome'] if responsavel_id else None

            field_display_names = {
                'titular': 'Titular', 'matricula': 'Matrícula', 'tipo_id': 'Tipo de Serviço',
                'data_entrada': 'Data de Entrada', 'status_id': 'Status', 'prazo_final': 'Prazo Final',
                'apresentante': 'Apresentante', 'apresentante_telefone': 'Telefone Apresentante',
                'apresentante_email': 'E-mail Apresentante', 'responsavel_id': 'Responsável',
                'envolvido_notas': 'Envolve Notas', 'observacoes': 'Observações', 'data_conclusao': 'Data de Conclusão'
            }

            for field, display_name in field_display_names.items():
                old_value = old_processo_data.get(field)
                new_value = current_data.get(field)

                old_value_display = old_value
                new_value_display = new_value

                if field == 'tipo_id':
                    old_value_display = tipo_nome_antigo
                    new_value_display = tipo_nome_novo
                elif field == 'status_id':
                    old_value_display = status_nome_antigo
                    new_value_display = status_nome_novo
                elif field == 'responsavel_id':
                    old_value_display = responsavel_nome_antigo
                    new_value_display = responsavel_nome_novo
                elif field == 'envolvido_notas':
                    old_value_display = "Sim" if old_value else "Não"
                    new_value_display = "Sim" if new_value else "Não"
                elif field in ['data_entrada', 'prazo_final', 'data_conclusao']:
                    if isinstance(old_value, str) and old_value:
                        try:
                            old_value_display = datetime.strptime(old_value.split(' ')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
                        except ValueError:
                            old_value_display = old_value
                    if isinstance(new_value, str) and new_value:
                        try:
                            new_value_display = datetime.strptime(new_value.split(' ')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
                        except ValueError:
                            new_value_display = new_value
                        
                if str(old_value_display or '').strip() != str(new_value_display or '').strip():
                    registrar_historico_processo(
                        processo_id=processo_id,
                        usuario_id=responsavel_id,
                        campo_alterado=display_name,
                        valor_antigo=str(old_value_display) if old_value_display is not None else "",
                        valor_novo=str(new_value_display) if new_value_display is not None else "",
                        connection=connection
                    )
            
            logger.info(f"Processo '{processo_id}' atualizado com sucesso no DB.")
        return rows_affected
    except sqlite3.IntegrityError as e:
        logger.warning(f"Tentativa de atualizar processo '{processo_id}' com erro de integridade. Erro: {e}")
        raise ValueError("Erro de integridade ao atualizar processo.") from e
    except Exception as e:
        logger.error(f"Erro ao atualizar processo '{processo_id}': {e}", exc_info=True)
        raise

def excluir_processo_db(processo_id, connection):
    """
    Exclui um processo e mantém o titular desvinculado (sem perda de dados do titular).
    """
    try:
        # Desvincula o titular explicitamente (caso FK não propague em todas versões do SQLite)
        executar_query(
            "UPDATE titulares SET ultimo_registro_id = NULL, updated_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime') WHERE ultimo_registro_id = ?",
            [processo_id], connection=connection
        )

        rows_affected = executar_query(
            "DELETE FROM processos WHERE id = ?",
            [processo_id],
            connection=connection
        )
        
        if rows_affected > 0:
            logger.info(f"Processo ID {processo_id} excluído com sucesso da tabela 'processos'.")
            return True
        else:
            logger.warning(f"Tentativa de excluir o processo ID {processo_id}, mas não foi encontrado.")
            return False

    except Exception as e:
        logger.error(f"Erro no modelo ao excluir o processo ID {processo_id}: {e}", exc_info=True)
        raise e


def registrar_historico_processo(processo_id, usuario_id, campo_alterado, valor_antigo, valor_novo, observacao_adicional=None, connection=None):
    if connection:
        conn = connection
        close_conn = False
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        close_conn = True

    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO historico_processos (processo_id, usuario_id, campo_alterado, valor_antigo, valor_novo, observacao_adicional, timestamp_alteracao)
            VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """
        cursor.execute(query, [processo_id, usuario_id, campo_alterado, valor_antigo, valor_novo, observacao_adicional])
        if close_conn:
            conn.commit()
        logger.debug(f"Histórico registrado para processo {processo_id}: Campo '{campo_alterado}', Antigo: '{valor_antigo}', Novo: '{valor_novo}', Obs: '{observacao_adicional}'")
    except Exception as e:
        logger.error(f"Erro ao registrar histórico para processo {processo_id}: {e}", exc_info=True)
        if close_conn:
            conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()


def obter_historico_processo(processo_id):
    query = """
        SELECT
            hp.id,
            hp.processo_id,
            hp.usuario_id,
            hp.campo_alterado,
            hp.valor_antigo,
            hp.valor_novo,
            hp.observacao_adicional,
            hp.timestamp_alteracao,
            U.nome AS usuario_nome
        FROM
            historico_processos hp
        LEFT JOIN
            usuarios U ON hp.usuario_id = U.id
        WHERE
            hp.processo_id = ?
        ORDER BY
            hp.timestamp_alteracao DESC, hp.id DESC
    """
    return executar_query(query, [processo_id], fetch_all=True)


def listar_processos(filtros, pagina_atual, registros_por_pagina, ordenar, ignore_default_filters=False): # MODIFICADO: Adicionado ignore_default_filters
    base_query = """
        SELECT
            P.id, P.numero_processo, P.titular, P.matricula,
            P.data_entrada, P.prazo_final, P.envolvido_notas,
            TS.nome AS tipo_nome,
            SP.nome AS status_nome, SP.hex_color AS status_hex,
            U.nome AS responsavel_nome
        FROM
            processos P
        JOIN
            tipos_servico TS ON P.tipo_id = TS.id
        JOIN
            status_processo SP ON P.status_id = SP.id
        LEFT JOIN
            usuarios U ON P.responsavel_id = U.id
    """
    count_query = "SELECT COUNT(P.id) AS total_count FROM processos P " \
                  "JOIN tipos_servico TS ON P.tipo_id = TS.id " \
                  "JOIN status_processo SP ON P.status_id = SP.id " \
                  "LEFT JOIN usuarios U ON P.responsavel_id = U.id "

    where_clauses = []
    query_params = []

    # MODIFICADO: Aplica filtros padrão APENAS SE ignore_default_filters for False
    if not ignore_default_filters:
        if filtros.get('status_id'):
            where_clauses.append("P.status_id = ?")
            query_params.append(filtros['status_id'])
        
        if 'status_ids_in' in filtros and filtros['status_ids_in']:
            placeholders = ','.join('?' * len(filtros['status_ids_in']))
            where_clauses.append(f"P.status_id IN ({placeholders})")
            query_params.extend(filtros['status_ids_in'])
        
        if filtros.get('filtro_pendentes_dashboard'):
            where_clauses.append("SP.nome LIKE '%Pendente%' AND SP.nome != 'Finalizado'")

        if filtros.get('filtro_em_andamento'):
            where_clauses.append("SP.nome != 'Finalizado' AND P.data_conclusao IS NULL")
        
        if filtros.get('responsavel_id'):
            where_clauses.append("P.responsavel_id = ?")
            query_params.append(filtros['responsavel_id'])
        
        # Note: Busca, data_inicio, data_fim, e envolve_notas são filtros manuais do usuário,
        # e geralmente são mantidos mesmo para 'suporte', a menos que a intenção seja *realmente* ver tudo.
        # Se a intenção é ignorar TUDO (incluindo busca), então essa lógica precisaria ser mais abrangente.
        # Por enquanto, assumirei que a busca manual e filtros de data/notas AINDA se aplicam se o suporte os usar.

    # ... (restante da função listar_processos) ...
    if filtros.get('tipo'):
        where_clauses.append("P.tipo_id = ?")
        query_params.append(filtros['tipo'])
    if filtros.get('busca'):
        busca_termo = f"%{filtros['busca']}%"
        # A busca já contempla P.matricula LIKE ?, então a funcionalidade de pesquisar pelo número da matrícula já está presente na lógica de busca global.
        where_clauses.append("(P.numero_processo LIKE ? OR P.titular LIKE ? OR P.matricula LIKE ? OR U.nome LIKE ? OR TS.nome LIKE ? OR SP.nome LIKE ?)")
        query_params.extend([busca_termo, busca_termo, busca_termo, busca_termo, busca_termo, busca_termo])
    if filtros.get('data_inicio'):
        where_clauses.append("P.data_entrada >= ?")
        query_params.append(filtros['data_inicio'])
    if filtros.get('data_fim'):
        where_clauses.append("P.data_entrada <= ?")
        query_params.append(filtros['data_fim'])
    if filtros.get('envolve_notas') is not None:
        where_clauses.append("P.envolvido_notas = ?")
        query_params.append(filtros['envolve_notas'])
    
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
        count_query += " WHERE " + " AND ".join(where_clauses)

    order_map = {
        'data_entrada_asc': 'P.data_entrada ASC',
        'data_entrada_desc': 'P.data_entrada DESC',
        'titular_asc': 'P.titular COLLATE NOCASE ASC',
        'titular_desc': 'P.titular COLLATE NOCASE DESC',
        'tipo_asc': 'TS.nome COLLATE NOCASE ASC',
        'tipo_desc': 'TS.nome COLLATE NOCASE DESC',
        'status_asc': 'SP.nome COLLATE NOCASE ASC',
        'status_desc': 'SP.nome COLLATE NOCASE DESC',
        'id_asc': 'P.id ASC',
        'id_desc': 'P.id DESC',
        'matricula_asc': 'P.matricula COLLATE NOCASE ASC',
        'matricula_desc': 'P.matricula COLLATE NOCASE DESC',
        'prazo_asc': 'P.prazo_final ASC, P.id DESC',
        'prazo_desc': 'P.prazo_final DESC, P.id DESC',
    }
    order_by_clause = order_map.get(ordenar, 'P.id DESC')
    base_query += f" ORDER BY {order_by_clause}"

    offset = (pagina_atual - 1) * registros_por_pagina
    
    base_query += " LIMIT ? OFFSET ?"
    params_for_data_query = list(query_params)
    params_for_data_query.extend([registros_por_pagina, offset])

    total_registros_result = executar_query(count_query, query_params, fetch_one=True)
    total_records = total_registros_result['total_count'] if total_registros_result and 'total_count' in total_registros_result else 0
    total_pages = (total_records + registros_por_pagina - 1) // registros_por_pagina
    if total_pages == 0 and total_records > 0:
        total_pages = 1

    processos = executar_query(base_query, params_for_data_query, fetch_all=True)

    return {
        'processos': processos,
        'total_records': total_records,
        'total_pages': total_pages
    }

def get_total_processes_count():
    result = executar_query("SELECT COUNT(id) AS total_count FROM processos", fetch_one=True)
    return result['total_count'] if result and 'total_count' in result else 0

def get_concluidos_processes_count():
    """Conta processos com status 'Finalizado'."""
    result = executar_query(
        "SELECT COUNT(P.id) AS total_count FROM processos P JOIN status_processo SP ON P.status_id = SP.id WHERE SP.nome = 'Finalizado'",
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_overdue_processes_count():
    hoje = datetime.now().strftime('%Y-%m-%d')
    result = executar_query(
        "SELECT COUNT(P.id) AS total_count FROM processos P JOIN status_processo SP ON P.status_id = SP.id WHERE P.prazo_final < ? AND SP.nome != 'Finalizado'",
        [hoje],
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_in_progress_processes_count():
    """Conta processos com status 'Pendente%' e que não estão concluídos/arquivados/finalizados."""
    result = executar_query(
        "SELECT COUNT(P.id) AS total_count FROM processos P JOIN status_processo SP ON P.status_id = SP.id WHERE SP.nome LIKE 'Pendente%' AND SP.nome != 'Finalizado'",
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_today_processes_count():
    """Conta processos cuja data de entrada OU criação é hoje."""
    query = """
        SELECT COUNT(P.id) AS total_count FROM processos P
        WHERE strftime('%Y-%m-%d', P.data_entrada) = strftime('%Y-%m-%d', 'now', 'localtime')
           OR strftime('%Y-%m-%d', P.created_at)   = strftime('%Y-%m-%d', 'now', 'localtime')
    """
    result = executar_query(query, fetch_one=True)
    return result['total_count'] if result and 'total_count' in result else 0

def get_prenotados_processes_count():
    """Conta processos com status 'Prenotado'."""
    result = executar_query(
        """SELECT COUNT(P.id) AS total_count
           FROM processos P
           JOIN status_processo SP ON P.status_id = SP.id
           WHERE SP.nome = 'Prenotado'
             AND P.data_conclusao IS NULL""",
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0


def get_em_andamento_processes_count():
    """Conta todos os processos em andamento (não finalizados e sem data de conclusão)."""
    result = executar_query(
        """SELECT COUNT(P.id) AS total_count
           FROM processos P
           JOIN status_processo SP ON P.status_id = SP.id
           WHERE SP.nome != 'Finalizado'
             AND P.data_conclusao IS NULL""",
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_user_linked_processes_count(user_id):
    """Conta processos vinculados (responsável) ao usuário, excluindo finalizados/concluídos/arquivados."""
    result = executar_query(
        """SELECT COUNT(P.id) AS total_count
           FROM processos P
           JOIN status_processo SP ON P.status_id = SP.id
           WHERE P.responsavel_id = ?
             AND SP.nome != 'Finalizado'
             AND P.data_conclusao IS NULL""",
        [user_id],
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_recent_processes(limit=5):
    """
    Retorna processos recentes, excluindo status 'Finalizado'.
    """
    query = """
        SELECT
            P.id, P.titular, P.matricula, P.data_entrada,
            SP.nome AS status_nome, SP.hex_color AS status_hex
        FROM
            processos P
        JOIN
            status_processo SP ON P.status_id = SP.id
        WHERE
            SP.nome != 'Finalizado'
        ORDER BY
            P.created_at DESC, P.id DESC
        LIMIT ?
    """
    return executar_query(query, [limit])

def get_critical_deadline_processes(limit=5):
    hoje = datetime.now().strftime('%Y-%m-%d')
    query = """
        SELECT
            P.id, P.titular, P.matricula, P.prazo_final,
            SP.nome AS status_nome, SP.hex_color AS status_hex,
            TS.nome AS tipo_servico_nome
        FROM
            processos P
        JOIN
            status_processo SP ON P.status_id = SP.id
        LEFT JOIN
            tipos_servico TS ON P.tipo_id = TS.id
        WHERE
            SP.nome != 'Finalizado'
            AND P.prazo_final IS NOT NULL
            AND (
                P.prazo_final < ? OR
                date(P.prazo_final) BETWEEN date('now', 'localtime') AND date('now', 'localtime', '+5 days')
            )
        ORDER BY
            CASE
                WHEN P.prazo_final < ? THEN 1
                WHEN P.prazo_final = ? THEN 2
                WHEN P.prazo_final > ? AND P.prazo_final <= date('now', 'localtime', '+5 days') THEN 3
                ELSE 4
            END,
            P.prazo_final ASC,
            P.titular COLLATE NOCASE ASC,
            P.id DESC
        LIMIT ?
    """
    results = executar_query(query, [hoje, hoje, hoje, hoje, limit])
    
    for r in results:
        if isinstance(r['prazo_final'], str) and len(r['prazo_final']) >= 10:
            r['prazo_final_dt'] = datetime.strptime(r['prazo_final'].split(' ')[0], '%Y-%m-%d').date()
        else:
            r['prazo_final_dt'] = None
    return results


def obter_anexos_processo(processo_id):
    query = "SELECT id, nome_original, nome_arquivo, tipo, tamanho, data_upload FROM anexos_processos WHERE processo_id = ?"
    return executar_query(query, [processo_id])

def inserir_anexo_processo(processo_id, nome_original, nome_arquivo_servidor, mime_type, tamanho, usuario_upload_id, connection=None):
    query = """
        INSERT INTO anexos_processos
        (processo_id, nome_original, nome_arquivo, tipo, tamanho, data_upload, usuario_upload)
        VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), ?)
    """
    params = [processo_id, nome_original, nome_arquivo_servidor, mime_type, tamanho, usuario_upload_id]
    
    registrar_historico_processo(
        processo_id=processo_id,
        usuario_id=usuario_upload_id,
        campo_alterado='anexo',
        valor_antigo=None,
        valor_novo=nome_original,
        observacao_adicional=f"Anexo '{nome_original}' adicionado.",
        connection=connection
    )

    return executar_query(query, params, connection=connection)

def excluir_anexo_processo(anexo_id, processo_id, connection=None):
    query = "SELECT nome_arquivo, nome_original FROM anexos_processos WHERE id = ? AND processo_id = ?"
    result = executar_query(query, [anexo_id, processo_id], fetch_one=True, connection=connection)
    if result:
        rows_affected = executar_query("DELETE FROM anexos_processos WHERE id = ?", [anexo_id], connection=connection)
        if rows_affected:
            registrar_historico_processo(
                processo_id=processo_id,
                usuario_id=None,
                campo_alterado='anexo',
                valor_antigo=result['nome_original'],
                valor_novo=None,
                observacao_adicional=f"Anexo '{result['nome_original']}' removido.",
                connection=connection
            )
            return result['nome_arquivo']
    return None

def acquire_lock(table_name, record_id, user_id, timeout_minutes):
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        
        now_dt = datetime.now()
        cursor.execute("DELETE FROM record_locks WHERE expires_at < ?", [now_dt.strftime('%Y-%m-%d %H:%M:%S')])
        logger.debug(f"Locks expirados para {table_name}:{record_id} limpos.")

        cursor.execute("SELECT user_id, locked_at, expires_at FROM record_locks WHERE table_name = ? AND record_id = ?",
                       [table_name, record_id])
        existing_lock = cursor.fetchone()

        if existing_lock:
            locked_by_user_id = existing_lock['user_id']
            expires_at_str = existing_lock['expires_at']
            expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')

            if locked_by_user_id == user_id:
                new_expires_at = now_dt + timedelta(minutes=timeout_minutes)
                cursor.execute("UPDATE record_locks SET expires_at = ?, locked_at = ? WHERE table_name = ? AND record_id = ?",
                               [new_expires_at.strftime('%Y-%m-%d %H:%M:%S'), now_dt.strftime('%Y-%m-%d %H:%M:%S'), table_name, record_id])
                logger.info(f"Lock para {table_name}:{record_id} renovado por usuário {user_id}. Expira em: {new_expires_at}")
                return True
            elif now_dt < expires_at:
                user_info = executar_query("SELECT nome FROM usuarios WHERE id = ?", [locked_by_user_id], fetch_one=True, connection=conn)
                locked_by_name = user_info['nome'] if user_info else f"Usuário (ID {locked_by_user_id})"
                logger.warning(f"Tentativa de adquirir lock em {table_name}:{record_id} por {user_id}. Já bloqueado por {locked_by_name} até {expires_at}.")
                return {'error': f"Este registro está sendo editado por {locked_by_name}. Tente novamente mais tarde (expira em {expires_at.strftime('%H:%M:%S')}).", 'type': 'warning', 'code': 409}
            else:
                cursor.execute("DELETE FROM record_locks WHERE table_name = ? AND record_id = ?", [table_name, record_id])
                logger.info(f"Lock expirado para {table_name}:{record_id} por usuário {locked_by_user_id} removido. Tentando adquirir novo lock.")
        
        # Correção da sintaxe aqui: minutes=timeout_minutes
        new_expires_at = now_dt + timedelta(minutes=timeout_minutes)
        try:
            cursor.execute("INSERT INTO record_locks (table_name, record_id, user_id, locked_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                           [table_name, record_id, user_id, now_dt.strftime('%Y-%m-%d %H:%M:%S'), new_expires_at.strftime('%Y-%m-%d %H:%M:%S')])
            logger.info(f"Lock em {table_name}:{record_id} adquirido por usuário {user_id}. Expira em: {new_expires_at}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Falha de integridade ao adquirir lock para {table_name}:{record_id} por {user_id}. Conflito de concorrência. Retrying acquire_lock...")
            return acquire_lock(table_name, record_id, user_id, timeout_minutes)
        except Exception as e:
            logger.error(f"Erro inesperado ao adquirir lock para {table_name}:{record_id} por {user_id}: {e}", exc_info=True)
            return {'error': 'Erro interno ao tentar bloquear o registro.', 'type': 'danger', 'code': 500}

# --- INÍCIO DA CORREÇÃO DE FLUXO DE TRABALHO DE RECUPERAÇÃO DE SENHA ---

def release_lock(table_name, record_id, user_id):
    """
    Liberta um bloqueio de registo específico para um utilizador.
    """
    try:
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            
            # ESTA É A LINHA CRÍTICA CORRIGIDA:
            # Apaga o bloqueio para a tabela e registo específicos que pertencem ao utilizador atual.
            cursor.execute(
                "DELETE FROM record_locks WHERE table_name = ? AND record_id = ? AND user_id = ?",
                [table_name, record_id, user_id]
            )
            
            rows_affected = cursor.rowcount
            
            if rows_affected > 0:
                logger.info(f"Lock para {table_name}:{record_id} libertado com sucesso pelo utilizador {user_id}.")
                return {'success': True}
            else:
                # Log informativo de que o bloqueio não foi encontrado, pois provavelmente já havia sido liberado.
                logger.info(f"Lock de {table_name}:{record_id} não encontrado - já expirado ou liberado.")
                return {'success': False, 'message': 'O bloqueio não foi encontrado para ser libertado.'}

    except Exception as e:
        logger.error(f"Erro inesperado ao libertar lock para {table_name}:{record_id}: {e}", exc_info=True)
        return {'success': False, 'error': 'Erro interno do servidor ao tentar libertar o bloqueio.'}

def renew_lock(table_name, record_id, user_id, timeout_minutes):
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        
        now_dt = datetime.now()
        new_expires_at = now_dt + timedelta(minutes=timeout_minutes)
        
        cursor.execute("UPDATE record_locks SET expires_at = ?, locked_at = ? WHERE table_name = ? AND record_id = ? AND user_id = ? AND expires_at > ?",
                       [new_expires_at.strftime('%Y-%m-%d %H:%M:%S'), now_dt.strftime('%Y-%m-%d %H:%M:%S'), table_name, record_id, user_id, now_dt.strftime('%Y-%m-%d %H:%M:%S')])
        rows_affected = cursor.rowcount
        
        if rows_affected > 0:
            logger.debug(f"Lock para {table_name}:{record_id} renovado com sucesso por usuário {user_id}.")
            return {'success': True}
        else:
            logger.warning(f"Falha ao renovar lock para {table_name}:{record_id} por {user_id}. Tentando readquirir...")
            return acquire_lock(table_name, record_id, user_id, timeout_minutes)
            
def release_all_locks(user_id):
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM record_locks WHERE user_id = ?", [user_id])
        rows_affected = cursor.rowcount
        if rows_affected > 0:
            logger.info(f"{rows_affected} locks liberados para o usuário {user_id}.")
        return {'success': True, 'count': rows_affected}

def add_status_processo(nome, hex_color):
    validar_nome_unico_db('status_processo', 'nome', nome)
    return executar_query(
        "INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)",
        [nome, hex_color, 1]
    )

def update_status_processo(status_id, nome, hex_color, ativo):
    current_status = executar_query("SELECT nome, ativo FROM status_processo WHERE id = ?", [status_id], fetch_one=True)
    if not current_status:
        raise ValueError("Status não encontrado para edição.")

    validar_nome_unico_db('status_processo', 'nome', nome, status_id)
        
    return executar_query(
        "UPDATE status_processo SET nome = ?, hex_color = ?, ativo = ? WHERE id = ?",
        [nome, hex_color, 1 if ativo else 0, status_id]
    )

def toggle_status_processo(status_id):
    current_status = executar_query("SELECT nome, ativo FROM status_processo WHERE id = ?", [status_id], fetch_one=True)
    if not current_status:
        raise ValueError("Status não encontrado.")
    
    novo_status = not current_status['ativo']
    
    if current_status['ativo'] == 1 and not novo_status:
        count_in_use = executar_query("SELECT COUNT(*) FROM processos WHERE status_id = ?", [status_id], fetch_one=True)['COUNT(*)']
        if count_in_use > 0:
            raise ValueError(f"Não foi possível desativar o status '{current_status['nome']}' porque ele está sendo utilizado por {count_in_use} processo(s).")

    return executar_query(
        "UPDATE status_processo SET ativo = ? WHERE id = ?",
        [1 if novo_status else 0, status_id]
    )

def add_tipo_servico(nome, descricao, prazo_padrao):
    if prazo_padrao is None or prazo_padrao < 0:
        prazo_padrao = 30
    validar_nome_unico_db('tipos_servico', 'nome', nome)
    return executar_query(
        "INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)",
        [nome, descricao, 1, prazo_padrao]
    )

def update_tipo_servico(service_id, nome, descricao, ativo, prazo_padrao):
    current_service = executar_query("SELECT nome, ativo FROM tipos_servico WHERE id = ?", [service_id], fetch_one=True)
    if not current_service:
        raise ValueError("Tipo de serviço não encontrado para edição.")

    if prazo_padrao is None or prazo_padrao < 0:
        prazo_padrao = 30
    validar_nome_unico_db('tipos_servico', 'nome', nome, service_id)

    return executar_query(
        "UPDATE tipos_servico SET nome = ?, descricao = ?, ativo = ?, prazo_padrao = ? WHERE id = ?",
        [nome, descricao, 1 if ativo else 0, prazo_padrao, service_id]
    )

def toggle_tipo_servico(service_id):
    current_service = executar_query("SELECT nome, ativo FROM tipos_servico WHERE id = ?", [service_id], fetch_one=True)
    if not current_service:
        raise ValueError("Tipo de serviço não encontrado.")

    novo_status = not current_service['ativo']

    if current_service['ativo'] == 1 and not novo_status:
        count_in_use = executar_query("SELECT COUNT(*) FROM processos WHERE tipo_id = ?", [service_id], fetch_one=True)['COUNT(*)']
        if count_in_use > 0:
            raise ValueError(f"Não foi possível desativar o serviço '{current_service['nome']}' porque ele está sendo utilizado por {count_in_use} processo(s).")
            
    return executar_query(
        "UPDATE tipos_servico SET ativo = ? WHERE id = ?",
        [1 if novo_status else 0, service_id]
    )

def get_email_config():
    config = {
        'id': None,
        'smtp_host': '',
        'smtp_port': 587,
        'smtp_encryption': 'tls',
        'smtp_username': '',
        'smtp_password': '',
        'sender_email': '',
        'sender_name': 'Registro Fácil',
        'ativo': 0
    }
    
    result = executar_query("SELECT id, smtp_host, smtp_port, smtp_encryption, smtp_username, smtp_password, sender_email, sender_name, ativo FROM email_config LIMIT 1", fetch_one=True)
    if result:
        config.update(result)
        if config['smtp_password']:
            decrypted_pass = decrypt(config['smtp_password'])
            config['smtp_password'] = decrypted_pass if decrypted_pass is not None else ''
        else:
            config['smtp_password'] = ''
    
    return config

def save_email_config(config_data, is_new_config=False, connection=None):
    smtp_password_raw = config_data.get('smtp_password')
    encrypted_password = None

    # Resolve se é INSERT ou UPDATE: prioriza o ID informado,
    # mas também verifica se já existe um registro com o mesmo smtp_username
    # (evita UNIQUE constraint ao salvar após um teste bem-sucedido sem ID).
    config_id = config_data.get('id')
    if not config_id or config_id <= 0:
        existing = executar_query(
            "SELECT id FROM email_config WHERE smtp_username = ? LIMIT 1",
            [config_data['smtp_username']], fetch_one=True, connection=connection
        )
        if existing:
            config_id = existing['id']
        else:
            any_existing = executar_query(
                "SELECT id FROM email_config LIMIT 1",
                fetch_one=True, connection=connection
            )
            if any_existing:
                config_id = any_existing['id']

    is_update = bool(config_id and config_id > 0)

    if smtp_password_raw:
        encrypted_password = encrypt(smtp_password_raw)
        if encrypted_password is None:
            logger.error("Falha ao criptografar a senha. Retornando erro.")
            raise ValueError("Falha ao criptografar a senha. Verifique a chave de criptografia.")
    elif is_update:
        current_config_db = executar_query(
            "SELECT smtp_password FROM email_config WHERE id = ? LIMIT 1",
            [config_id], fetch_one=True, connection=connection
        )
        if current_config_db:
            encrypted_password = current_config_db['smtp_password']

    if config_data.get('ativo'):
        executar_query(
            "UPDATE email_config SET ativo = 0 WHERE ativo = 1 AND id != ?",
            [config_id or 0], connection=connection
        )

    if not is_update:
        if not smtp_password_raw:
            raise ValueError("A senha SMTP é obrigatória para uma nova configuração.")
        res = executar_query(
            """INSERT INTO email_config (smtp_host, smtp_port, smtp_encryption, smtp_username, smtp_password, sender_email, sender_name, ativo, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))""",
            [config_data['smtp_host'], config_data['smtp_port'], config_data['smtp_encryption'],
             config_data['smtp_username'], encrypted_password, config_data['sender_email'],
             config_data['sender_name'], config_data['ativo']],
            connection=connection
        )
        return bool(res)
    else:
        res = executar_query(
            """UPDATE email_config SET smtp_host = ?, smtp_port = ?, smtp_encryption = ?,
               smtp_username = ?, smtp_password = ?, sender_email = ?, sender_name = ?, ativo = ?,
               updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
               WHERE id = ?""",
            [config_data['smtp_host'], config_data['smtp_port'], config_data['smtp_encryption'],
             config_data['smtp_username'], encrypted_password, config_data['sender_email'],
             config_data['sender_name'], config_data['ativo'], config_id],
            connection=connection
        )
        return bool(res)


def send_email(to_address, subject, body, sender_name=None, sender_email=None, app_instance=None):
    from flask_mail import Message, Mail # Mantenha a importação aqui

    if app_instance is None:
        logger.error("send_email chamado sem a instância 'app_instance'. Não é possível enviar o e-mail.")
        return False, "Erro interno: Instância do aplicativo Flask não fornecida para envio de e-mail."

    email_config = get_email_config()
    if not email_config or not email_config.get('ativo'):
        logger.warning("Tentativa de enviar e-mail, mas a configuração de e-mail não está ativa ou não foi encontrada.")
        return False, "Configuração de e-mail não ativa ou não encontrada."

    _sender_name = sender_name if sender_name else email_config['sender_name']
    _sender_email = sender_email if sender_email else email_config['sender_email']

    # Salva as configurações originais antes de modificá-las
    original_mail_configs = {
        'MAIL_SERVER': app_instance.config.get('MAIL_SERVER'),
        'MAIL_PORT': app_instance.config.get('MAIL_PORT'),
        'MAIL_USE_TLS': app_instance.config.get('MAIL_USE_TLS'),
        'MAIL_USE_SSL': app_instance.config.get('MAIL_USE_SSL'),
        'MAIL_USERNAME': app_instance.config.get('MAIL_USERNAME'),
        'MAIL_PASSWORD': app_instance.config.get('MAIL_PASSWORD'),
        'MAIL_DEFAULT_SENDER': app_instance.config.get('MAIL_DEFAULT_SENDER')
    }

    # <----- PONTO CRÍTICO DA CORREÇÃO: Atualize app.config PRIMEIRO ----->
    app_instance.config['MAIL_SERVER'] = email_config['smtp_host']
    app_instance.config['MAIL_PORT'] = email_config['smtp_port']
    app_instance.config['MAIL_USE_TLS'] = (email_config['smtp_encryption'] == 'tls')
    app_instance.config['MAIL_USE_SSL'] = (email_config['smtp_encryption'] == 'ssl')
    app_instance.config['MAIL_USERNAME'] = email_config['smtp_username']
    app_instance.config['MAIL_PASSWORD'] = email_config['smtp_password'] # Já descriptografado por get_email_config
    app_instance.config['MAIL_DEFAULT_SENDER'] = (_sender_name, _sender_email)

    logger.debug(f"DEBUG E-MAIL: Configurações de envio a serem usadas:")
    logger.debug(f"  MAIL_SERVER: {app_instance.config.get('MAIL_SERVER')}")
    logger.debug(f"  MAIL_PORT: {app_instance.config.get('MAIL_PORT')}")
    logger.debug(f"  MAIL_USE_TLS: {app_instance.config.get('MAIL_USE_TLS')}")
    logger.debug(f"  MAIL_USE_SSL: {app_instance.config.get('MAIL_USE_SSL')}")
    logger.debug(f"  MAIL_USERNAME: {app_instance.config.get('MAIL_USERNAME')}")
    logger.debug(f"  MAIL_PASSWORD: {'(senha presente)' if app_instance.config.get('MAIL_PASSWORD') else '(senha ausente)'}")
    logger.debug(f"  MAIL_DEFAULT_SENDER: {app_instance.config.get('MAIL_DEFAULT_SENDER')}")
    logger.debug(f"  Destinatário: {to_address}, Assunto: {subject}")

    # <----- PONTO CRÍTICO DA CORREÇÃO: Crie o objeto Mail SOMENTE AGORA ----->
    mail_instance = Mail(app_instance) 

    msg = Message(subject, sender=(_sender_name, _sender_email), recipients=[to_address])
    msg.body = body

    try:
        with app_instance.app_context():
            mail_instance.send(msg)
        logger.info(f"E-mail enviado com sucesso para {to_address} (Assunto: {subject}).")
        return True, "E-mail enviado com sucesso."
    except Exception as e:
        logger.error(f"Falha ao enviar e-mail para {to_address} (Assunto: {subject}): {e}", exc_info=True)
        return False, f"Falha ao enviar e-mail: {e}"
    finally:
        # Restaura as configurações originais
        for key, value in original_mail_configs.items():
            if value is not None:
                app_instance.config[key] = value
            elif key in app_instance.config: # Se a chave não existia originalmente, remova-a
                del app_instance.config[key]


def test_db_connection():
    logger.info(f"Testando conexão SQLite com o caminho '{DATABASE_PATH}'.")
    try:
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
        logger.info(f"Conexão SQLite com '{DATABASE_PATH}' bem-sucedida.")
        return True
    except Exception as e:
        logger.error(f"Falha na conexão SQLite com '{DATABASE_PATH}': {e}", exc_info=True)
        raise ValueError(f"Conexão com o banco SQLite falhou: {e}")

def optimize_database():
    """
    Otimiza o banco de dados SQLite executando o comando VACUUM.
    O VACUUM desfragmenta o arquivo do banco de dados e recupera espaço não utilizado.
    """
    logger.info(f"Iniciando otimização do banco de dados '{DATABASE_PATH}'.")
    try:
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            # VACUUM não pode ser executado dentro de uma transação
            conn.isolation_level = None
            cursor.execute("VACUUM")
            conn.isolation_level = ''
        logger.info(f"Otimização do banco de dados '{DATABASE_PATH}' concluída com sucesso.")
        return True
    except Exception as e:
        logger.error(f"Erro ao otimizar banco de dados '{DATABASE_PATH}': {e}", exc_info=True)
        return False


def check_and_repair_database():
    """
    Verifica a integridade do banco de dados SQLite e tenta reparar problemas de corrupção.
    
    Estratégia de reparo:
      1. PRAGMA integrity_check — identifica páginas corrompidas.
      2. PRAGMA quick_check — verificação rápida adicional.
      3. REINDEX — reconstrói todos os índices (corrige corrupção de índice).
      4. VACUUM — reescreve o arquivo do banco em um novo arquivo limpo,
                  eliminando páginas danificadas recuperáveis.
    
    Retorna um dict com:
      - ok (bool): True se o banco passou na verificação ou foi reparado.
      - integrity_result (list): linhas retornadas pelo integrity_check.
      - repaired (bool): True se alguma ação de reparo foi realizada.
      - details (list): log das ações executadas.
      - error (str|None): mensagem de erro fatal, se houver.
    """
    result = {
        'ok': False,
        'integrity_result': [],
        'repaired': False,
        'details': [],
        'error': None
    }
    
    logger.info(f"Iniciando verificação de integridade do banco de dados '{DATABASE_PATH}'.")
    
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # --- 1. integrity_check ---
        try:
            cursor.execute("PRAGMA integrity_check(100)")
            rows = cursor.fetchall()
            integrity_lines = [r[0] for r in rows]
            result['integrity_result'] = integrity_lines
            result['details'].append(f"integrity_check: {integrity_lines}")
            logger.info(f"Resultado do integrity_check: {integrity_lines}")
        except sqlite3.DatabaseError as e:
            integrity_lines = [f"ERRO AO EXECUTAR integrity_check: {e}"]
            result['integrity_result'] = integrity_lines
            result['details'].append(integrity_lines[0])
            logger.error(f"Erro ao executar PRAGMA integrity_check: {e}", exc_info=True)

        # --- 2. quick_check ---
        try:
            cursor.execute("PRAGMA quick_check(10)")
            qrows = cursor.fetchall()
            quick_lines = [r[0] for r in qrows]
            result['details'].append(f"quick_check: {quick_lines}")
            logger.info(f"Resultado do quick_check: {quick_lines}")
        except sqlite3.DatabaseError as e:
            result['details'].append(f"quick_check falhou: {e}")
            logger.warning(f"quick_check falhou: {e}")

        is_clean = (len(integrity_lines) == 1 and integrity_lines[0].lower() == 'ok')

        if is_clean:
            result['ok'] = True
            result['details'].append("Banco de dados íntegro. Nenhum reparo necessário.")
            logger.info("Banco de dados passou na verificação de integridade. Nenhum reparo necessário.")
            conn.close()
            return result

        # --- 3. Banco corrompido: tentar REINDEX ---
        logger.warning(f"Banco de dados com problemas de integridade. Tentando REINDEX...")
        result['details'].append("Banco corrompido. Iniciando REINDEX...")
        try:
            conn.isolation_level = None  # autocommit para REINDEX
            cursor.execute("REINDEX")
            conn.isolation_level = ''
            result['repaired'] = True
            result['details'].append("REINDEX concluído com sucesso.")
            logger.info("REINDEX concluído com sucesso.")
        except sqlite3.DatabaseError as e:
            result['details'].append(f"REINDEX falhou: {e}")
            logger.error(f"REINDEX falhou: {e}", exc_info=True)

        # --- 4. VACUUM para reescrever arquivo ---
        logger.info("Executando VACUUM para reescrever o arquivo do banco...")
        result['details'].append("Iniciando VACUUM (reescrita do arquivo)...")
        try:
            conn.isolation_level = None
            cursor.execute("VACUUM")
            conn.isolation_level = ''
            result['repaired'] = True
            result['details'].append("VACUUM concluído com sucesso. Arquivo reescrito.")
            logger.info("VACUUM concluído. O arquivo do banco foi reescrito.")
        except sqlite3.DatabaseError as e:
            result['details'].append(f"VACUUM falhou: {e}")
            logger.error(f"VACUUM falhou durante reparo: {e}", exc_info=True)

        # --- 5. Verificação pós-reparo ---
        try:
            cursor.execute("PRAGMA integrity_check(100)")
            post_rows = cursor.fetchall()
            post_lines = [r[0] for r in post_rows]
            result['details'].append(f"integrity_check pós-reparo: {post_lines}")
            logger.info(f"integrity_check pós-reparo: {post_lines}")
            if len(post_lines) == 1 and post_lines[0].lower() == 'ok':
                result['ok'] = True
                result['details'].append("Banco de dados reparado com sucesso!")
                logger.info("Banco de dados reparado com sucesso após REINDEX + VACUUM.")
                # Ativa WAL mode após reparo para prevenir corrupção futura
                try:
                    conn.isolation_level = None
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    conn.isolation_level = ''
                    result['details'].append("WAL mode ativado para prevenir corrupção futura.")
                    logger.info("WAL mode ativado com sucesso após reparo.")
                except Exception as wal_e:
                    result['details'].append(f"WAL mode não pôde ser ativado: {wal_e}")
                    logger.warning(f"Não foi possível ativar WAL mode após reparo: {wal_e}")
            else:
                result['ok'] = False
                result['details'].append("Banco ainda apresenta problemas após reparo. Restaure um backup.")
                logger.error("Banco ainda corrompido após tentativa de reparo. Restauração de backup necessária.")
        except sqlite3.DatabaseError as e:
            result['details'].append(f"Verificação pós-reparo falhou: {e}")
            logger.error(f"Verificação pós-reparo falhou: {e}")

        conn.close()

    except sqlite3.DatabaseError as e:
        result['error'] = str(e)
        result['details'].append(f"Erro fatal ao acessar o banco: {e}")
        logger.critical(f"Erro fatal ao verificar/reparar banco de dados: {e}", exc_info=True)
    except Exception as e:
        result['error'] = str(e)
        result['details'].append(f"Erro inesperado: {e}")
        logger.critical(f"Erro inesperado ao verificar/reparar banco: {e}", exc_info=True)

    return result


def reconstruct_database():
    """
    Reconstrução nuclear do banco de dados usando iterdump().

    Lê linha a linha de todas as tabelas (ignorando páginas corrompidas),
    gera SQL INSERT para cada registro recuperável, cria um arquivo .db novo
    e substitui o original.

    Use quando VACUUM/REINDEX não resolverem o erro 'database disk image is malformed'.

    Retorna dict com: ok, rows_recovered, rows_skipped, backup_path, details, error.
    """
    import shutil, tempfile

    result = {
        'ok': False,
        'rows_recovered': 0,
        'rows_skipped': 0,
        'backup_path': None,
        'details': [],
        'error': None
    }

    logger.info("Iniciando RECONSTRUÇÃO NUCLEAR do banco de dados via iterdump().")
    result['details'].append("Iniciando reconstrução completa do banco de dados...")

    # 1. Backup do arquivo original
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = DATABASE_PATH + f".backup_pre_rebuild_{timestamp_str}"
    try:
        shutil.copy2(DATABASE_PATH, backup_path)
        result['backup_path'] = backup_path
        result['details'].append(f"Backup criado: {backup_path}")
        logger.info(f"Backup pré-reconstrução: {backup_path}")
    except Exception as e:
        result['error'] = f"Falha ao criar backup antes da reconstrução: {e}"
        result['details'].append(result['error'])
        logger.critical(result['error'])
        return result

    # 2. Arquivo temporário para o banco novo
    new_db_fd, new_db_path = tempfile.mkstemp(
        suffix='.db',
        prefix='rf_rebuilt_',
        dir=os.path.dirname(DATABASE_PATH)
    )
    os.close(new_db_fd)

    src_conn = None
    dst_conn = None

    try:
        src_conn = sqlite3.connect(DATABASE_PATH, timeout=30)
        dst_conn = sqlite3.connect(new_db_path, timeout=30)
        dst_conn.execute("PRAGMA journal_mode=WAL")
        dst_conn.execute("PRAGMA synchronous=NORMAL")
        dst_conn.isolation_level = None  # autocommit

        # 3. iterdump: itera CREATE TABLE + INSERTs do banco corrompido
        recovered = 0
        skipped = 0
        sql_statements = []
        try:
            for line in src_conn.iterdump():
                sql_statements.append(line)
                recovered += 1
        except Exception as dump_e:
            result['details'].append(f"iterdump interrompido: {dump_e}")
            logger.warning(f"iterdump interrompido: {dump_e}")

        # 4. Executar no banco novo
        exec_errors = 0
        for stmt in sql_statements:
            try:
                dst_conn.execute(stmt)
            except sqlite3.Error as ex:
                exec_errors += 1
                logger.debug(f"Stmt ignorado: {ex} | {stmt[:80]}")

        result['rows_recovered'] = recovered
        result['rows_skipped'] = skipped + exec_errors
        result['details'].append(
            f"iterdump: {recovered} instruções recuperadas, {exec_errors} ignoradas."
        )

        src_conn.close(); src_conn = None
        dst_conn.isolation_level = ''
        dst_conn.close(); dst_conn = None

        # 5. Integridade do novo banco
        vc = sqlite3.connect(new_db_path, timeout=10)
        integrity = [r[0] for r in vc.execute("PRAGMA integrity_check(5)").fetchall()]
        vc.close()
        result['details'].append(f"Integridade do banco reconstruído: {integrity}")
        logger.info(f"Integridade banco reconstruído: {integrity}")

        # 6. Substituir banco original
        # Remover arquivos WAL/SHM para evitar conflito
        for ext in ['-wal', '-shm']:
            wp = DATABASE_PATH + ext
            if os.path.exists(wp):
                try: os.remove(wp)
                except: pass

        shutil.move(new_db_path, DATABASE_PATH)
        result['ok'] = True
        result['details'].append(
            f"Banco reconstruído e substituído com sucesso! "
            f"{recovered} instruções recuperadas."
        )
        logger.info("Reconstrução concluída. Banco substituído.")

        # 7. Recriar tabelas ausentes (ex: record_locks, etc.)
        # iterdump pode pular tabelas com constraints; init_db garante o esquema completo.
        try:
            init_db()
            result['details'].append("Esquema verificado/recriado com sucesso após reconstrução.")
            logger.info("init_db() executado após reconstrução — tabelas ausentes recriadas.")
        except Exception as init_e:
            result['details'].append(f"Aviso: init_db pós-reconstrução: {init_e}")
            logger.warning(f"init_db pós-reconstrução: {init_e}")

    except Exception as e:
        result['error'] = str(e)
        result['details'].append(f"Erro durante reconstrução: {e}")
        logger.critical(f"Erro durante reconstrução: {e}", exc_info=True)
    finally:
        if src_conn:
            try: src_conn.close()
            except: pass
        if dst_conn:
            try: dst_conn.close()
            except: pass
        if not result['ok'] and os.path.exists(new_db_path):
            try: os.remove(new_db_path)
            except: pass

    return result

def get_users_for_admin_list(filters, page, per_page, order_by):
    base_query = """
        SELECT id, usuario, nome, email, created_at, ativo, deleted_at, role
        FROM usuarios U
    """
    count_query = "SELECT COUNT(*) AS total_count FROM usuarios U"

    where_clauses = []
    query_params = []

    if filters.get('status') == 'ativo':
        where_clauses.append("U.ativo = 1")
    elif filters.get('status') == 'inativo':
        where_clauses.append("U.ativo = 0")
    
    if filters.get('busca'):
        search_term = f"%{filters['busca']}%"
        where_clauses.append("(U.usuario LIKE ? OR U.nome LIKE ? OR U.email LIKE ?)")
        query_params.extend([search_term, search_term, search_term])
    
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
        count_query += " WHERE " + " AND ".join(where_clauses)

    order_map = {
        'id_asc': 'U.id ASC',
        'id_desc': 'U.id DESC',
        'usuario_asc': 'U.usuario COLLATE NOCASE ASC',
        'usuario_desc': 'U.usuario COLLATE NOCASE DESC',
        'nome_asc': 'U.nome COLLATE NOCASE ASC',
        'nome_desc': 'U.nome COLLATE NOCASE DESC',
        'email_asc': 'U.email COLLATE NOCASE ASC',
        'email_desc': 'U.email COLLATE NOCASE DESC',
        'created_at_asc': 'U.created_at ASC',
        'created_at_desc': 'U.created_at DESC',
        'status_asc': 'U.ativo ASC, U.created_at DESC',
        'status_desc': 'U.ativo DESC, U.created_at DESC',
    }
    order_clause = order_map.get(order_by, 'U.ativo DESC, U.created_at DESC')
    base_query += f" ORDER BY {order_clause}"

    offset = (page - 1) * per_page
    
    base_query = f"{base_query} LIMIT ? OFFSET ?"
    query_params_for_data = list(query_params)
    query_params_for_data.extend([per_page, offset])

    total_records_result = executar_query(count_query, query_params, fetch_one=True)
    total_records = total_records_result['total_count'] if total_records_result and 'total_count' in total_records_result else 0
    total_pages = (total_records + per_page - 1) // per_page
    if total_pages == 0 and total_records > 0:
        total_pages = 1

    users = executar_query(base_query, query_params_for_data)

    return {
        'users': users,
        'total_records': total_records,
        'total_pages': total_pages
    }

def get_empresa_info():
    return executar_query("""
        SELECT id, cartorio, oficial, substituta, endereco,
               telefone, email, logo,
               criado_em, atualizado_em
        FROM empresa LIMIT 1""", fetch_one=True)

def save_empresa_info(data, is_new_record=False, connection=None):
    if data.get('email') and not validar_email(data['email']):
        raise ValueError("E-mail da empresa inválido.")

    if data.get('telefone') and not validar_telefone(data['telefone']):
        raise ValueError("Telefone da empresa inválido.")

    field_mapping = {
        'cartorio': 'cartorio',
        'oficial': 'oficial',
        'substituta': 'substituta',
        'endereco': 'endereco',
        'telefone': 'telefone',
        'email': 'email',
        'logo': 'logo'
    }
    
    filtered_data = {}
    for k, v in data.items():
        if k in field_mapping:
            filtered_data[field_mapping[k]] = v

    if is_new_record:
        if 'logo' in filtered_data and not filtered_data['logo']:
            del filtered_data['logo']
        
        columns = ', '.join(filtered_data.keys())
        placeholders = ', '.join(['?'] * len(filtered_data))
        query = f"INSERT INTO empresa ({columns}, criado_em, atualizado_em) VALUES ({placeholders}, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))"
        return executar_query(query, list(filtered_data.values()), connection=connection)
    else:
        update_fields = []
        update_params = []
        for k_lower, v in filtered_data.items():
            if k_lower == 'logo':
                if v is None or v == '':
                    update_fields.append(f"{k_lower} = NULL")
                else:
                    update_fields.append(f"{k_lower} = ?")
                    update_params.append(v)
            else:
                update_fields.append(f"{k_lower} = ?")
                update_params.append(v)
        
        query = f"UPDATE empresa SET {', '.join(update_fields)}, atualizado_em = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?"
        update_params.append(data['id'])
        
        return executar_query(query, update_params, connection=connection)

def get_backup_config():
    default_config = {
        'id': None,
        'local_path': Config.BACKUP_ROOT_DIR, 
        'cloud_provider': 'none',
        'sftp_host': '',
        'sftp_port': 22,
        'sftp_username': '',
        'sftp_password': '',
        'sftp_remote_path': '/backups/',
        'auto_backup_enabled': 0,
        'backup_frequency': 'daily',
        'backup_time': '02:00',
        'backup_days': [],
        'backup_day_of_month': 1,
        'last_backup_at': None
    }
    
    result = executar_query("SELECT * FROM backup_configs LIMIT 1", fetch_one=True)
    if result:
        config = dict(result)
        if config.get('sftp_password'):
            decrypted_pass = decrypt(config['sftp_password'])
            config['sftp_password'] = decrypted_pass if decrypted_pass is not None else ''
        else:
            config['sftp_password'] = ''
        
        if config.get('backup_days'):
            config['backup_days'] = config['backup_days'].split(',')
        else:
            config['backup_days'] = []
        
        default_config.update(config)
    return default_config

def save_backup_config(config_data, connection=None):
    sftp_password_raw = config_data.get('sftp_password')
    encrypted_sftp_password = None

    if sftp_password_raw:
        encrypted_sftp_password = encrypt(sftp_password_raw)
        if encrypted_sftp_password is None:
            logger.error("Falha ao criptografar a nova senha SFTP. Retornando erro.")
            raise ValueError("Falha ao criptografar a senha SFTP. Verifique a chave de criptografia.")
    elif config_data.get('id'):
        current_sftp_pass_result = executar_query("SELECT sftp_password FROM backup_configs WHERE id = ? LIMIT 1", [config_data['id']], fetch_one=True, connection=connection)
        if current_sftp_pass_result:
            encrypted_sftp_password = current_sftp_pass_result['sftp_password']
        logger.debug(f"Senha SFTP não fornecida, usando a senha existente (se houver) para config ID: {config_data.get('id')}")

    backup_days_db_format = ''
    if isinstance(config_data.get('backup_days'), list):
        backup_days_db_format = ','.join(config_data['backup_days'])
    elif config_data.get('backup_days') is not None:
        backup_days_db_format = str(config_data['backup_days'])

    auto_backup_enabled_db = 1 if config_data.get('auto_backup_enabled') in [1, '1', 'on', True] else 0
        
    params = [
        config_data.get('local_path'),
        config_data.get('cloud_provider'),
        config_data.get('sftp_host'),
        config_data.get('sftp_port'),
        config_data.get('sftp_username'),
        encrypted_sftp_password,
        config_data.get('sftp_remote_path'),
        auto_backup_enabled_db,
        config_data.get('backup_frequency'),
        config_data.get('backup_time'),
        backup_days_db_format,
        config_data.get('backup_day_of_month'),
        config_data.get('uploads_path')
    ]
    
    if config_data.get('id'):
        query = """
            UPDATE backup_configs SET
            local_path = ?, cloud_provider = ?, sftp_host = ?, sftp_port = ?,
            sftp_username = ?, sftp_password = ?, sftp_remote_path = ?,
            auto_backup_enabled = ?, backup_frequency = ?, backup_time = ?,
            backup_days = ?, backup_day_of_month = ?, uploads_path = ?,
            updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
            WHERE id = ?
        """
        params.append(config_data['id'])
        logger.debug(f"Atualizando backup_configs. ID: {config_data['id']}, Auto enabled: {auto_backup_enabled_db}")
        return executar_query(query, params, connection=connection)
    else:
        query = """
            INSERT INTO backup_configs (
                local_path, cloud_provider, sftp_host, sftp_port, sftp_username, sftp_password, sftp_remote_path,
                auto_backup_enabled, backup_frequency, backup_time, backup_days, backup_day_of_month, uploads_path,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """
        logger.debug(f"Inserindo nova backup_config. Auto enabled: {auto_backup_enabled_db}")
        return executar_query(query, params, connection=connection)

def update_last_backup_time(connection=None):
    config = get_backup_config()
    
    query = "UPDATE backup_configs SET last_backup_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = (SELECT id FROM backup_configs LIMIT 1)"
    logger.info("Atualizando last_backup_at no DB.")
    return executar_query(query, connection=connection)

def create_password_reset_token(user_id, expires_in_minutes=60):
    # token: segredo completo, nunca exposto na URL
    token = secrets.token_urlsafe(64)
    # short_id: identificador público curto e opaco para a URL (ex: aB3xK9mQ)
    short_id = secrets.token_urlsafe(8)

    expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
    expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')

    try:
        executar_query(
            "DELETE FROM password_reset_tokens WHERE user_id = ? AND is_used = 0 AND expires_at < strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')",
            [user_id]
        )
        executar_query(
            "INSERT INTO password_reset_tokens (user_id, token, short_id, expires_at, is_used, created_at) VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))",
            [user_id, token, short_id, expires_at_str, 0]
        )
        logger.info(f"Token de redefinição de senha gerado para usuário ID: {user_id}. Expira em {expires_at_str}.")
        return short_id  # Retorna apenas o short_id — é o que vai na URL
    except Exception as e:
        logger.error(f"Erro ao criar token de redefinição de senha para usuário ID {user_id}: {e}", exc_info=True)
        raise

def get_password_reset_token(short_id_string):
    """Busca o token pelo short_id (identificador público da URL)."""
    query = """
        SELECT
            prt.id AS token_id, prt.user_id, prt.token, prt.short_id, prt.expires_at, prt.is_used,
            u.nome AS user_nome, u.email AS user_email
        FROM
            password_reset_tokens prt
        JOIN
            usuarios u ON prt.user_id = u.id
        WHERE
            prt.short_id = ?
        LIMIT 1
    """
    token_data = executar_query(query, [short_id_string], fetch_one=True)

    if not token_data:
        logger.warning(f"Tentativa de usar token de redefinição não encontrado (short_id): {short_id_string[:6]}...")
        return None

    if token_data['is_used'] == 1:
        logger.warning(f"Tentativa de usar token de redefinição já utilizado (short_id): {short_id_string[:6]}... (ID: {token_data['token_id']})")
        return None

    return {
        'token_id': token_data['token_id'],
        'user_id': token_data['user_id'],
        'token': token_data['token'],
        'short_id': token_data['short_id'],
        'expires_at': token_data['expires_at'],
        'is_used': token_data['is_used']
    }

def mark_password_reset_token_as_used(token_id, connection=None):
    try:
        query = "UPDATE password_reset_tokens SET is_used = 1, updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?"
        rows = executar_query(query, [token_id], connection=connection)
        
        if rows > 0:
            logger.info(f"Token de redefinição de senha ID {token_id} marcado como usado.")
            return True
        return False
    except Exception as e:
        logger.error(f"Erro ao marcar token de redefinição de senha ID {token_id} como usado: {e}", exc_info=True)
        raise # Propaga o erro para o rollback da transação

def is_record_locked(table_name, record_id, current_user_id):
    """
    Verifica se um registro está bloqueado por OUTRO usuário.
    Retorna os dados do bloqueio se estiver bloqueado, caso contrário, retorna None.
    """
    from datetime import datetime
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Primeiro, limpa locks expirados para garantir que a verificação seja precisa.
    try:
        executar_query("DELETE FROM record_locks WHERE expires_at < ?", [now_str])
    except Exception as e:
        logger.error(f"Falha ao limpar locks expirados antes da verificação: {e}")

    # Agora, verifica se existe um lock ativo para o registro que não pertence ao usuário atual.
    lock_info = executar_query(
        """
        SELECT L.user_id, U.nome as user_nome
        FROM record_locks L
        JOIN usuarios U ON L.user_id = U.id
        WHERE L.table_name = ? AND L.record_id = ? AND L.user_id != ?
        """,
        [table_name, record_id, current_user_id],
        fetch_one=True
    )
    
    return lock_info if lock_info else None

# --- Funções para Titulares ---

def listar_titulares(filtros=None, pagina=1, registros_por_pagina=10):
    """Lista titulares com paginação e filtros."""
    import math
    offset = (pagina - 1) * registros_por_pagina
    
    query = """SELECT t.*,
               CASE WHEN p.id IS NULL THEN NULL
                    WHEN (p.possui_matricula = 1 OR (p.possui_matricula IS NULL AND p.matricula IS NOT NULL)) AND p.matricula IS NOT NULL THEN p.matricula
                    ELSE 'Sem Matrícula'
               END as ultimo_registro_matricula,
               (SELECT COUNT(*) FROM processos pr
                  WHERE pr.titular_id = t.id
                     OR (pr.titular_id IS NULL AND pr.titular = t.nome)) as total_processos
               FROM titulares t LEFT JOIN processos p ON t.ultimo_registro_id = p.id WHERE 1=1"""
    params = []
    
    if filtros:
        if filtros.get('busca'):
            query += " AND (t.nome LIKE ? OR t.email LIKE ? OR t.telefone LIKE ?)"
            busca = f"%{filtros['busca']}%"
            params.extend([busca, busca, busca])
            
    # Obter total de registros para paginação
    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_records = executar_query(count_query, params, fetch_one=True)['COUNT(*)']
    
    # Ordenação dinâmica
    ordenar = filtros.get('ordenar', 'nome') if filtros else 'nome'
    direcao = filtros.get('direcao', 'asc') if filtros else 'asc'
    
    colunas_validas = {'nome': 't.nome', 'email': 't.email', 'telefone': 't.telefone', 'processos': 'total_processos'}
    col_sql = colunas_validas.get(ordenar, 't.nome')
    dir_sql = 'DESC' if direcao == 'desc' else 'ASC'
    
    query += f" ORDER BY {col_sql} {dir_sql} LIMIT ? OFFSET ?"
    params.extend([registros_por_pagina, offset])
    
    titulares = executar_query(query, params, fetch_all=True)
    
    return {
        'titulares': titulares,
        'total_records': total_records,
        'total_pages': math.ceil(total_records / registros_por_pagina) if total_records > 0 else 0
    }

def get_titular_by_id(titular_id):
    """Obtém detalhes de um titular pelo ID."""
    query = """SELECT t.*,
               CASE WHEN p.id IS NULL THEN NULL
                    WHEN (p.possui_matricula = 1 OR (p.possui_matricula IS NULL AND p.matricula IS NOT NULL)) AND p.matricula IS NOT NULL THEN p.matricula
                    ELSE 'Sem Matrícula'
               END as ultimo_registro_matricula
               FROM titulares t LEFT JOIN processos p ON t.ultimo_registro_id = p.id WHERE t.id = ?"""
    return executar_query(query, [titular_id], fetch_one=True)

def titular_tem_processos(titular_id):
    """Verifica vínculo por ID e mantém fallback para processos legados."""
    tit = executar_query("SELECT nome FROM titulares WHERE id = ?", [titular_id], fetch_one=True)
    if not tit:
        return False
    result = executar_query(
        """
        SELECT COUNT(*) AS cnt
          FROM processos
         WHERE titular_id = ?
            OR (titular_id IS NULL AND titular = ?)
        """,
        [titular_id, tit['nome']],
        fetch_one=True,
    )
    return result['cnt'] > 0 if result else False

def _sincronizar_processos_cadastro(
    cadastro_id,
    nome_anterior,
    nome_novo,
    telefone_novo,
    email_novo,
    tipo_cadastro,
    usuario_id=None,
    processo_excluido_id=None,
    connection=None,
):
    """Propaga dados de um cadastro para processos e audita as mudanças."""
    if not cadastro_id:
        return []
    if tipo_cadastro not in {'titular', 'apresentante'}:
        raise ValueError("Tipo de cadastro inválido para sincronização.")

    nome_coluna = tipo_cadastro
    id_coluna = f"{tipo_cadastro}_id"
    telefone_coluna = f"{tipo_cadastro}_telefone"
    email_coluna = f"{tipo_cadastro}_email"

    where_sql = f"{id_coluna} = ?"
    params = [cadastro_id]
    if nome_anterior:
        where_sql += f" OR ({id_coluna} IS NULL AND {nome_coluna} = ?)"
        params.append(nome_anterior)

    processos = executar_query(
        f"""
        SELECT id, {nome_coluna} AS nome_atual,
               {telefone_coluna} AS telefone_atual,
               {email_coluna} AS email_atual
          FROM processos
         WHERE {where_sql}
        """,
        params,
        fetch_all=True,
        connection=connection,
    ) or []

    alteracoes = []
    prefixo = 'titular' if tipo_cadastro == 'titular' else 'apresentante'
    nomes_exibicao = {
        'nome': 'Titular' if tipo_cadastro == 'titular' else 'Apresentante',
        'telefone': f"Telefone do {prefixo}",
        'email': f"E-mail do {prefixo}",
    }

    for processo in processos:
        if processo_excluido_id is not None and int(processo['id']) == int(processo_excluido_id):
            continue

        nome_antigo_processo = processo['nome_atual'] or ''
        telefone_antigo_processo = processo['telefone_atual'] or ''
        email_antigo_processo = processo['email_atual'] or ''
        valores = [nome_novo, cadastro_id, telefone_novo, email_novo]

        executar_query(
            f"""
            UPDATE processos
               SET {nome_coluna} = ?, {id_coluna} = ?,
                   {telefone_coluna} = ?, {email_coluna} = ?,
                   updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
             WHERE id = ?
            """,
            valores + [processo['id']],
            connection=connection,
        )

        comparacoes = [
            ('nome', nome_antigo_processo, nome_novo or ''),
            ('telefone', telefone_antigo_processo, telefone_novo or ''),
            ('email', email_antigo_processo, email_novo or ''),
        ]
        for campo, valor_antigo, valor_novo in comparacoes:
            if str(valor_antigo).strip() == str(valor_novo).strip():
                continue
            registrar_historico_processo(
                processo_id=processo['id'],
                usuario_id=usuario_id,
                campo_alterado=nomes_exibicao[campo],
                valor_antigo=str(valor_antigo),
                valor_novo=str(valor_novo),
                observacao_adicional=(
                    f"Alteração sincronizada a partir do cadastro "
                    f"{tipo_cadastro} ID {cadastro_id}."
                ),
                connection=connection,
            )
            alteracoes.append(processo['id'])

    return sorted(set(alteracoes))


def editar_titular(titular_id, nome, telefone, email, connection=None, usuario_id=None):
    """Atualiza um titular e sincroniza os processos que armazenam seu nome."""
    from datetime import datetime

    if connection is None:
        with get_sqlite_connection() as conn:
            return editar_titular(titular_id, nome, telefone, email, connection=conn, usuario_id=usuario_id)

    titular_atual = executar_query(
        "SELECT nome, telefone, email FROM titulares WHERE id = ?",
        [titular_id],
        fetch_one=True,
        connection=connection,
    )
    if not titular_atual:
        return False

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    nome_anterior = titular_atual['nome']

    executar_query(
        "UPDATE titulares SET nome = ?, telefone = ?, email = ?, updated_at = ? WHERE id = ?",
        [nome, telefone, email, now, titular_id],
        connection=connection,
    )

    _sincronizar_processos_cadastro(
        cadastro_id=titular_id,
        nome_anterior=nome_anterior,
        nome_novo=nome,
        telefone_novo=telefone,
        email_novo=email,
        tipo_cadastro='titular',
        usuario_id=usuario_id,
        connection=connection,
    )
    return True

def excluir_titular(titular_id, connection=None):
    """Exclui um titular sem processos vinculados."""
    rows = executar_query("DELETE FROM titulares WHERE id = ?", [titular_id], connection=connection)
    return rows

def get_historico_servicos_titular(titular_id_ou_nome):
    """Obtém o histórico por titular_id, com fallback para processos legados."""
    if isinstance(titular_id_ou_nome, int):
        where_sql = "p.titular_id = ? OR (p.titular_id IS NULL AND p.titular = (SELECT nome FROM titulares WHERE id = ?))"
        params = [titular_id_ou_nome, titular_id_ou_nome]
    else:
        where_sql = "p.titular = ?"
        params = [titular_id_ou_nome]

    query = f"""
        SELECT p.*, ts.nome as tipo_servico_nome, sp.nome as status_nome, sp.hex_color
        FROM processos p
        JOIN tipos_servico ts ON p.tipo_id = ts.id
        JOIN status_processo sp ON p.status_id = sp.id
        WHERE {where_sql}
        ORDER BY p.data_entrada DESC
    """
    return executar_query(query, params, fetch_all=True)

def upsert_titular_from_processo(titular_nome, telefone, email, processo_id, connection=None, nome_anterior=None, cadastro_id=None, usuario_id=None, processo_excluido_id=None):
    """Cria ou atualiza um titular sem duplicar quando um processo é renomeado."""
    from datetime import datetime
    if not titular_nome:
        return None
    if connection is None:
        with get_sqlite_connection() as conn:
            return upsert_titular_from_processo(
                titular_nome,
                telefone,
                email,
                processo_id,
                connection=conn,
                nome_anterior=nome_anterior,
                cadastro_id=cadastro_id,
                usuario_id=usuario_id,
                processo_excluido_id=processo_excluido_id,
            )
        
    # O ID é a identidade principal. Assim, editar nome, telefone ou e-mail
    # pelo processo altera o cadastro original, mesmo que o nome tenha mudado.
    titular = None
    if cadastro_id:
        titular = executar_query(
            "SELECT id, nome, telefone, email FROM titulares WHERE id = ?",
            [cadastro_id],
            fetch_one=True,
            connection=connection,
        )

    if titular is None:
        titular = executar_query(
            "SELECT id, nome, telefone, email FROM titulares WHERE nome = ?",
            [titular_nome],
            fetch_one=True,
            connection=connection,
        )
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if titular:
        # Buscar dados atuais para não sobrescrever com vazio
        titular_atual = executar_query("SELECT telefone, email FROM titulares WHERE id = ?", [titular['id']], fetch_one=True, connection=connection)
        
        novo_telefone = telefone if telefone else titular_atual['telefone']
        novo_email = email if email else titular_atual['email']
        
        # Atualizar dados existentes
        query_update = """
            UPDATE titulares 
            SET telefone = ?, email = ?, ultimo_registro_id = ?, updated_at = ? 
            WHERE id = ?
        """
        nome_atual = titular.get('nome') or titular_nome
        nome_final = titular_nome if cadastro_id else nome_atual
        executar_query(
            "UPDATE titulares SET nome = ?, telefone = ?, email = ?, ultimo_registro_id = ?, updated_at = ? WHERE id = ?",
            [nome_final, novo_telefone, novo_email, processo_id, now, titular['id']],
            connection=connection,
        )
        _sincronizar_processos_cadastro(
            cadastro_id=titular['id'],
            nome_anterior=nome_atual,
            nome_novo=nome_final,
            telefone_novo=novo_telefone,
            email_novo=novo_email,
            tipo_cadastro='titular',
            usuario_id=usuario_id,
            processo_excluido_id=processo_excluido_id,
            connection=connection,
        )
        return titular['id']
    else:
        # Se o nome anterior pertencia exclusivamente a este processo, trata a
        # alteração como edição do mesmo cadastro. Quando o nome antigo está
        # compartilhado por outros processos, cria-se um novo cadastro apenas
        # para este processo, preservando os demais vínculos.
        if nome_anterior and nome_anterior != titular_nome:
            titular_anterior = executar_query(
                "SELECT id FROM titulares WHERE nome = ?",
                [nome_anterior],
                fetch_one=True,
                connection=connection,
            )
            if titular_anterior:
                total_processos = executar_query(
                    """
                    SELECT COUNT(*) AS total
                      FROM processos
                     WHERE titular_id = ?
                        OR (titular_id IS NULL AND titular = ?)
                    """,
                    [titular_anterior['id'], nome_anterior],
                    fetch_one=True,
                    connection=connection,
                )
                if total_processos and total_processos['total'] <= 1:
                    executar_query(
                        """
                        UPDATE titulares
                           SET nome = ?, telefone = ?, email = ?, ultimo_registro_id = ?, updated_at = ?
                         WHERE id = ?
                        """,
                        [titular_nome, telefone, email, processo_id, now, titular_anterior['id']],
                        connection=connection,
                    )
                    _sincronizar_processos_cadastro(
                        cadastro_id=titular_anterior['id'],
                        nome_anterior=nome_anterior,
                        nome_novo=titular_nome,
                        telefone_novo=telefone,
                        email_novo=email,
                        tipo_cadastro='titular',
                        usuario_id=usuario_id,
                        processo_excluido_id=processo_excluido_id,
                        connection=connection,
                    )
                    return titular_anterior['id']

        # Inserir novo titular
        query_insert = """
            INSERT INTO titulares (nome, telefone, email, ultimo_registro_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = connection.cursor()
        cursor.execute(query_insert, [titular_nome, telefone, email, processo_id, now, now])
        return cursor.lastrowid

def buscar_titulares_json(termo):
    """Busca titulares para o dropdown de pesquisa (AJAX). '%' lista todos."""
    if termo.strip() == '%':
        query = "SELECT id, nome, telefone, email FROM titulares ORDER BY nome ASC LIMIT 50"
        return executar_query(query, [], fetch_all=True)
    query = "SELECT id, nome, telefone, email FROM titulares WHERE nome LIKE ? OR email LIKE ? ORDER BY nome ASC LIMIT 20"
    like = f"%{termo}%"
    return executar_query(query, [like, like], fetch_all=True)


# ============================================
# FUNÇÕES DE PERFORMANCE E ÍNDICES - v3.2.3+
# ============================================

def criar_indices_performance(cursor):
    """Cria índices otimizados para melhorar performance das queries."""
    try:
        indices = [
            # Processos
            "CREATE INDEX IF NOT EXISTS idx_processos_status ON processos(status_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_tipo ON processos(tipo_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_responsavel ON processos(responsavel_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_created_at ON processos(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_processos_numero ON processos(numero_processo)",
            "CREATE INDEX IF NOT EXISTS idx_processos_matricula ON processos(matricula)",
            "CREATE INDEX IF NOT EXISTS idx_processos_prazo ON processos(prazo_final, data_conclusao)",
            
            # Anexos
            "CREATE INDEX IF NOT EXISTS idx_anexos_processo_id ON anexos_processos(processo_id)",
            
            # Histórico (coluna correta: timestamp_alteracao)
            "CREATE INDEX IF NOT EXISTS idx_historico_processo ON historico_processos(processo_id, timestamp_alteracao DESC)",
            "CREATE INDEX IF NOT EXISTS idx_historico_usuario ON historico_processos(usuario_id, timestamp_alteracao DESC)",
            
            # Titulares (removido índice cpf_cnpj pois a coluna não existe na tabela)
            "CREATE INDEX IF NOT EXISTS idx_titulares_nome ON titulares(nome)",
            
            # Usuários
            "CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_ativos ON usuarios(ativo)",
            
            # Logs
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs(usuario_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_logs_acao ON logs(acao, timestamp DESC)",
            
            # Login attempts
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip, tempo DESC)",
            
            # Notificações
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario ON notificacoes(usuario_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_lida ON notificacoes(usuario_id, lida)",
            
            # Permissões (v3.3.5)
            "CREATE INDEX IF NOT EXISTS idx_permissoes_usuario ON permissoes_usuarios(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_permissoes_modulo ON permissoes_usuarios(modulo_id)",
            "CREATE INDEX IF NOT EXISTS idx_permissoes_usuario_modulo ON permissoes_usuarios(usuario_id, modulo_id)",
            
            # Módulos Sistema (v3.3.5)
            "CREATE INDEX IF NOT EXISTS idx_modulos_categoria ON modulos_sistema(categoria, ordem)",
            "CREATE INDEX IF NOT EXISTS idx_modulos_ativo ON modulos_sistema(ativo)",

            # Perfis de Permissão
            "CREATE INDEX IF NOT EXISTS idx_perfis_permissao_nome ON perfis_permissao(nome)",
            "CREATE INDEX IF NOT EXISTS idx_perfis_modulos_perfil ON perfis_permissao_modulos(perfil_id)",
            "CREATE INDEX IF NOT EXISTS idx_usuario_perfil_usuario ON usuario_perfil(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_usuario_perfil_perfil ON usuario_perfil(perfil_id)",

            # Auditoria e Segurança (v3.16.5)
            "CREATE INDEX IF NOT EXISTS idx_auditoria_admin_id ON auditoria_admin(admin_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_afetado ON auditoria_admin(usuario_afetado_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auditoria_acao ON auditoria_admin(acao, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tentativas_usuario ON tentativas_acesso_nao_autorizado(usuario_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tentativas_ip ON tentativas_acesso_nao_autorizado(ip, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario_lida ON notificacoes_usuario(usuario_id, lida)",
        ]
        
        for index_sql in indices:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Índice já existe ou erro ao criar: {e}")
        
        logger.info("Índices de performance criados/verificados com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao criar índices: {e}", exc_info=True)


# ============================================
# FUNÇÕES DE BUSCA FULL-TEXT (FTS5) - v3.2.3+
# ============================================

def rebuild_fts_index(conn=None):
    """
    Reconstrói completamente o índice FTS5 (processos_fts).
    Dropa a tabela e os triggers, recria tudo do zero.
    Seguro chamar a qualquer momento — não afeta dados reais (processos).
    """
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DATABASE_PATH, timeout=30)
        conn.isolation_level = None  # autocommit
        close_conn = True

    try:
        cur = conn.cursor()
        # Drop triggers primeiro (dependem da tabela FTS)
        for trig in ['processos_fts_insert', 'processos_fts_update', 'processos_fts_delete']:
            try:
                cur.execute(f"DROP TRIGGER IF EXISTS {trig}")
            except Exception:
                pass

        # Drop a tabela FTS (e todas as shadow tables automaticamente)
        try:
            cur.execute("DROP TABLE IF EXISTS processos_fts")
        except Exception:
            pass

        # Recriar a tabela FTS5 — content table aponta para processos
        cur.execute("""
            CREATE VIRTUAL TABLE processos_fts USING fts5(
                id UNINDEXED,
                numero_processo,
                titular,
                matricula,
                apresentante,
                observacoes,
                content='processos',
                content_rowid='id'
            )
        """)

        # Triggers corretos para content table FTS5:
        # UPDATE deve ser DELETE + INSERT (não UPDATE direto)
        cur.execute("""
            CREATE TRIGGER processos_fts_insert
            AFTER INSERT ON processos BEGIN
                INSERT INTO processos_fts(rowid, numero_processo, titular, matricula, apresentante, observacoes)
                VALUES (new.id, new.numero_processo, new.titular, new.matricula, new.apresentante, new.observacoes);
            END
        """)
        cur.execute("""
            CREATE TRIGGER processos_fts_update
            AFTER UPDATE ON processos BEGIN
                DELETE FROM processos_fts WHERE rowid = old.id;
                INSERT INTO processos_fts(rowid, numero_processo, titular, matricula, apresentante, observacoes)
                VALUES (new.id, new.numero_processo, new.titular, new.matricula, new.apresentante, new.observacoes);
            END
        """)
        cur.execute("""
            CREATE TRIGGER processos_fts_delete
            AFTER DELETE ON processos BEGIN
                DELETE FROM processos_fts WHERE rowid = old.id;
            END
        """)

        # Popular o FTS com todos os processos existentes
        cur.execute("""
            INSERT INTO processos_fts(rowid, numero_processo, titular, matricula, apresentante, observacoes)
            SELECT id, numero_processo, titular, matricula, apresentante, observacoes
            FROM processos
        """)

        if close_conn:
            conn.isolation_level = ''

        logger.info("Índice FTS5 reconstruído com sucesso.")
        return True

    except Exception as e:
        logger.error(f"Erro ao reconstruir FTS5: {e}", exc_info=True)
        return False
    finally:
        if close_conn and conn:
            try:
                conn.close()
            except Exception:
                pass


def init_fts(cursor, conn):
    """Inicializa tabela FTS5 para busca full-text otimizada."""
    try:
        # Verificar se a tabela FTS já existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processos_fts'")
        fts_exists = cursor.fetchone() is not None

        if fts_exists:
            # Testar se o FTS está íntegro fazendo uma query simples
            try:
                cursor.execute("SELECT COUNT(*) FROM processos_fts")
                cursor.fetchone()
                # Teste de escrita: rebuild parcial para checar shadow tables
                cursor.execute("INSERT INTO processos_fts(processos_fts) VALUES('integrity-check')")
                # Se chegou aqui, FTS está ok — recria triggers corretos se necessário
                _ensure_fts_triggers(cursor)
            except Exception as fts_err:
                logger.warning(f"FTS5 corrompido detectado na inicialização ({fts_err}). Reconstruindo...")
                conn.commit()  # Fechar qualquer transação pendente
                rebuild_fts_index(conn)
                logger.info("FTS5 reconstruído automaticamente durante inicialização.")
            return

        # FTS não existe: criar do zero
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS processos_fts USING fts5(
                id UNINDEXED,
                numero_processo,
                titular,
                matricula,
                apresentante,
                observacoes,
                content='processos',
                content_rowid='id'
            )
        """)
        _ensure_fts_triggers(cursor)

        # Popular com dados existentes
        cursor.execute("SELECT COUNT(*) as total FROM processos")
        total_processos = cursor.fetchone()[0]
        if total_processos > 0:
            logger.info(f"Populando FTS com {total_processos} processos existentes...")
            cursor.execute("""
                INSERT INTO processos_fts(rowid, numero_processo, titular, matricula, apresentante, observacoes)
                SELECT id, numero_processo, titular, matricula, apresentante, observacoes
                FROM processos
            """)
            conn.commit()
            logger.info("FTS populado com sucesso.")

        logger.info("Full-Text Search (FTS5) inicializado com sucesso.")
    except Exception as e:
        logger.warning(f"FTS5 não disponível ou erro ao inicializar: {e}")


def _ensure_fts_triggers(cursor):
    """Garante que os triggers FTS5 existam com a lógica correta (DELETE+INSERT no update)."""
    # Drop triggers existentes para recriar com lógica correta
    for trig in ['processos_fts_insert', 'processos_fts_update', 'processos_fts_delete']:
        try:
            cursor.execute(f"DROP TRIGGER IF EXISTS {trig}")
        except Exception:
            pass

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS processos_fts_insert
        AFTER INSERT ON processos BEGIN
            INSERT INTO processos_fts(rowid, numero_processo, titular, matricula, apresentante, observacoes)
            VALUES (new.id, new.numero_processo, new.titular, new.matricula, new.apresentante, new.observacoes);
        END
    """)
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS processos_fts_update
        AFTER UPDATE ON processos BEGIN
            DELETE FROM processos_fts WHERE rowid = old.id;
            INSERT INTO processos_fts(rowid, numero_processo, titular, matricula, apresentante, observacoes)
            VALUES (new.id, new.numero_processo, new.titular, new.matricula, new.apresentante, new.observacoes);
        END
    """)
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS processos_fts_delete
        AFTER DELETE ON processos BEGIN
            DELETE FROM processos_fts WHERE rowid = old.id;
        END
    """)


def busca_full_text(termo, usuario_id=None, limit=50):
    """
    Busca usando FTS5 para resultados rápidos e relevantes.
    
    Args:
        termo: Termo de busca
        usuario_id: ID do usuário (para filtros de permissão no futuro)
        limit: Número máximo de resultados
    
    Returns:
        Lista de processos encontrados
    """
    try:
        # Preparar termo para FTS5 (adiciona wildcards para busca parcial)
        termo_fts = f'"{termo}"*' if termo else '*'
        
        query = """
            SELECT 
                p.*,
                t.nome as tipo_nome,
                s.nome as status_nome,
                s.hex_color as status_cor,
                u.nome as responsavel_nome,
                bm25(processos_fts) as relevancia
            FROM processos_fts fts
            JOIN processos p ON fts.id = p.id
            LEFT JOIN tipos_servico t ON p.tipo_id = t.id
            LEFT JOIN status_processo s ON p.status_id = s.id
            LEFT JOIN usuarios u ON p.responsavel_id = u.id
            WHERE processos_fts MATCH ?
            ORDER BY relevancia
            LIMIT ?
        """
        
        resultados = executar_query(query, [termo_fts, limit], fetch_all=True)
        return resultados or []
    except Exception as e:
        logger.warning(f"Busca FTS5 falhou, usando busca tradicional: {e}")
        # Fallback para busca tradicional se FTS falhar
        return busca_tradicional(termo, limit)


def busca_tradicional(termo, limit=50):
    """Busca tradicional com LIKE (fallback quando FTS não disponível)."""
    query = """
        SELECT 
            p.*,
            t.nome as tipo_nome,
            s.nome as status_nome,
            s.hex_color as status_cor,
            u.nome as responsavel_nome
        FROM processos p
        LEFT JOIN tipos_servico t ON p.tipo_id = t.id
        LEFT JOIN status_processo s ON p.status_id = s.id
        LEFT JOIN usuarios u ON p.responsavel_id = u.id
        WHERE 
            p.numero_processo LIKE ? OR
            p.titular LIKE ? OR
            p.matricula LIKE ? OR
            p.apresentante LIKE ? OR
            p.observacoes LIKE ?
        ORDER BY p.created_at DESC
        LIMIT ?
    """
    termo_like = f"%{termo}%"
    return executar_query(query, [termo_like] * 5 + [limit], fetch_all=True) or []


# ============================================
# FUNÇÕES DE TEMPLATES DE PROCESSOS - v3.2.3+
# ============================================

def criar_template(nome, descricao, tipo_id, status_id, prazo_dias, 
                   observacoes_padrao, usuario_id, publico=0):
    """Cria um novo template de processo."""
    query = """
        INSERT INTO templates_processos 
        (nome, descricao, tipo_id, status_id, prazo_dias, observacoes_padrao, usuario_criador, publico)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    return executar_query(query, [nome, descricao, tipo_id, status_id, 
                                  prazo_dias, observacoes_padrao, usuario_id, publico])


def listar_templates(usuario_id=None):
    """Lista templates disponíveis para o usuário."""
    if usuario_id:
        query = """
            SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome, s.hex_color as status_cor
            FROM templates_processos t
            LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
            LEFT JOIN status_processo s ON t.status_id = s.id
            WHERE t.publico = 1 OR t.usuario_criador = ?
            ORDER BY t.nome
        """
        return executar_query(query, [usuario_id], fetch_all=True) or []
    else:
        query = """
            SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome, s.hex_color as status_cor
            FROM templates_processos t
            LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
            LEFT JOIN status_processo s ON t.status_id = s.id
            WHERE t.publico = 1
            ORDER BY t.nome
        """
        return executar_query(query, fetch_all=True) or []


def obter_template(template_id):
    """Obtém um template específico."""
    query = """
        SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome
        FROM templates_processos t
        LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
        LEFT JOIN status_processo s ON t.status_id = s.id
        WHERE t.id = ?
    """
    return executar_query(query, [template_id], fetch_one=True)


def atualizar_template(template_id, dados):
    """Atualiza um template existente."""
    campos = []
    valores = []
    
    campos_permitidos = ['nome', 'descricao', 'tipo_id', 'status_id', 
                        'prazo_dias', 'observacoes_padrao', 'publico']
    
    for campo in campos_permitidos:
        if campo in dados:
            campos.append(f"{campo} = ?")
            valores.append(dados[campo])
    
    if not campos:
        return False
    
    campos.append("updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
    valores.append(template_id)
    
    query = f"UPDATE templates_processos SET {', '.join(campos)} WHERE id = ?"
    return executar_query(query, valores)


def excluir_template(template_id, usuario_id):
    """Exclui um template (apenas o criador pode excluir)."""
    query = "DELETE FROM templates_processos WHERE id = ? AND usuario_criador = ?"
    return executar_query(query, [template_id, usuario_id])


# ============================================
# FUNÇÕES DE NOTIFICAÇÕES - v3.2.3+
# ============================================

def criar_notificacao(usuario_id, tipo, titulo, mensagem, processo_id=None, 
                      url=None, prioridade='normal'):
    """Cria uma nova notificação para o usuário."""
    query = """
        INSERT INTO notificacoes 
        (usuario_id, tipo, titulo, mensagem, processo_id, url, prioridade)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    return executar_query(query, [usuario_id, tipo, titulo, mensagem, 
                                  processo_id, url, prioridade])


def listar_notificacoes_pendentes(usuario_id, limit=20):
    """Lista notificações não lidas do usuário."""
    query = """
        SELECT n.*, p.numero_processo, p.titular
        FROM notificacoes n
        LEFT JOIN processos p ON n.processo_id = p.id
        WHERE n.usuario_id = ? AND n.lida = 0
        ORDER BY n.prioridade DESC, n.created_at DESC
        LIMIT ?
    """
    return executar_query(query, [usuario_id, limit], fetch_all=True) or []


def marcar_notificacao_lida(notificacao_id, usuario_id):
    """Marca uma notificação como lida."""
    query = """
        UPDATE notificacoes 
        SET lida = 1, read_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
        WHERE id = ? AND usuario_id = ?
    """
    return executar_query(query, [notificacao_id, usuario_id])


def marcar_todas_lidas(usuario_id):
    """Marca todas as notificações do usuário como lidas."""
    query = """
        UPDATE notificacoes 
        SET lida = 1, read_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
        WHERE usuario_id = ? AND lida = 0
    """
    return executar_query(query, [usuario_id])


def gerar_notificacoes_prazos():
    """
    Gera notificações automáticas para processos com prazos vencendo.
    Deve ser executado pelo scheduler periodicamente.
    """
    try:
        # Processos vencendo nas próximas 24 horas
        query_vencendo = """
            SELECT p.id, p.responsavel_id, p.titular, p.prazo_final
            FROM processos p
            WHERE p.data_conclusao IS NULL
            AND p.responsavel_id IS NOT NULL
            AND p.prazo_final BETWEEN date('now') AND date('now', '+1 day')
        """
        vencendo = executar_query(query_vencendo, fetch_all=True) or []
        
        for proc in vencendo:
            # Verificar se já não existe notificação para este processo
            existe = executar_query(
                "SELECT id FROM notificacoes WHERE processo_id = ? AND tipo = 'prazo_vencendo' AND created_at >= date('now')",
                [proc['id']],
                fetch_one=True
            )
            
            if not existe:
                criar_notificacao(
                    usuario_id=proc['responsavel_id'],
                    tipo='prazo_vencendo',
                    titulo='⏰ Prazo Vencendo!',
                    mensagem=f'O processo "{proc["titular"]}" vence amanhã ({proc["prazo_final"]})',
                    processo_id=proc['id'],
                    url=f'/processos/visualizar/processo={proc["id"]}',
                    prioridade='alta'
                )
        
        # Processos já vencidos
        query_vencidos = """
            SELECT p.id, p.responsavel_id, p.titular, p.prazo_final
            FROM processos p
            WHERE p.data_conclusao IS NULL
            AND p.responsavel_id IS NOT NULL
            AND p.prazo_final < date('now')
            AND p.prazo_final >= date('now', '-7 days')
        """
        vencidos = executar_query(query_vencidos, fetch_all=True) or []
        
        for proc in vencidos:
            existe = executar_query(
                "SELECT id FROM notificacoes WHERE processo_id = ? AND tipo = 'prazo_vencido' AND created_at >= date('now')",
                [proc['id']],
                fetch_one=True
            )
            
            if not existe:
                criar_notificacao(
                    usuario_id=proc['responsavel_id'],
                    tipo='prazo_vencido',
                    titulo='🚨 Prazo Vencido!',
                    mensagem=f'O processo "{proc["titular"]}" está atrasado desde {proc["prazo_final"]}',
                    processo_id=proc['id'],
                    url=f'/processos/visualizar/processo={proc["id"]}',
                    prioridade='alta'
                )
        
        logger.info(f"Notificações de prazo geradas: {len(vencendo)} vencendo, {len(vencidos)} vencidos")
    except Exception as e:
        logger.error(f"Erro ao gerar notificações de prazos: {e}", exc_info=True)


# ============================================
# FUNÇÕES DE PREFERÊNCIAS DO USUÁRIO - v3.2.3+
# ============================================

def obter_preferencias_usuario(usuario_id):
    """Obtém as preferências do usuário."""
    query = "SELECT * FROM user_preferences WHERE usuario_id = ?"
    prefs = executar_query(query, [usuario_id], fetch_one=True)
    
    if not prefs:
        # Criar preferências padrão
        executar_query(
            "INSERT INTO user_preferences (usuario_id) VALUES (?)",
            [usuario_id]
        )
        prefs = executar_query(query, [usuario_id], fetch_one=True)
    
    return prefs


def atualizar_preferencias_usuario(usuario_id, dados):
    """Atualiza as preferências do usuário."""
    campos = []
    valores = []
    
    campos_permitidos = ['tema', 'notificacoes_push', 'notificacoes_email', 
                        'dashboard_layout', 'filtros_salvos']
    
    for campo in campos_permitidos:
        if campo in dados:
            campos.append(f"{campo} = ?")
            valores.append(dados[campo])
    
    if not campos:
        return False
    
    campos.append("updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
    valores.append(usuario_id)
    
    query = f"""
        UPDATE user_preferences 
        SET {', '.join(campos)} 
        WHERE usuario_id = ?
    """
    return executar_query(query, valores)


# ============================================
# FUNÇÕES DE AUDITORIA E SEGURANÇA - v3.3.3+
# ============================================

def gravar_auditoria_admin(admin_id, acao, justificativa, ip, usuario_afetado_id=None, 
                           campo_alterado=None, valor_anterior=None, valor_novo=None, 
                           user_agent=None):
    """
    Grava uma ação administrativa no log de auditoria.
    
    Args:
        admin_id: ID do administrador que realizou a ação
        acao: Tipo de ação ('reset_senha', 'inativacao', 'alteracao_role', etc)
        justificativa: Justificativa obrigatória da ação
        ip: IP do administrador
        usuario_afetado_id: ID do usuário afetado pela ação (opcional)
        campo_alterado: Nome do campo alterado (opcional)
        valor_anterior: Valor anterior do campo (opcional)
        valor_novo: Valor novo do campo (opcional)
        user_agent: User agent do navegador (opcional)
    
    Returns:
        ID do registro de auditoria criado
    """
    try:
        # Buscar informações do admin
        admin_data = executar_query(
            "SELECT nome, email FROM usuarios WHERE id = ?",
            [admin_id],
            fetch_one=True
        )
        
        admin_nome = admin_data['nome'] if admin_data else 'Desconhecido'
        admin_email = admin_data['email'] if admin_data else None
        
        # Buscar informações do usuário afetado, se aplicável
        usuario_afetado_nome = None
        usuario_afetado_email = None
        if usuario_afetado_id:
            user_data = executar_query(
                "SELECT nome, email FROM usuarios WHERE id = ?",
                [usuario_afetado_id],
                fetch_one=True
            )
            if user_data:
                usuario_afetado_nome = user_data['nome']
                usuario_afetado_email = user_data['email']
        
        # Inserir registro de auditoria
        query = """
            INSERT INTO auditoria_admin (
                admin_id, admin_nome, admin_email, acao, 
                usuario_afetado_id, usuario_afetado_nome, usuario_afetado_email,
                campo_alterado, valor_anterior, valor_novo, 
                justificativa, ip, user_agent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [
                admin_id, admin_nome, admin_email, acao,
                usuario_afetado_id, usuario_afetado_nome, usuario_afetado_email,
                campo_alterado, valor_anterior, valor_novo,
                justificativa, ip, user_agent
            ])
            audit_id = cursor.lastrowid
        
        logger.info(f"Auditoria registrada: {acao} por admin {admin_id} ({admin_nome}) - ID: {audit_id}")
        return audit_id
        
    except Exception as e:
        logger.error(f"Erro ao gravar auditoria administrativa: {e}", exc_info=True)
        return None


def gravar_tentativa_nao_autorizada(usuario_id, tipo_tentativa, ip, detalhes=None, 
                                    alvo_user_id=None, user_agent=None, bloqueado=True):
    """
    Grava uma tentativa de acesso não autorizado.
    
    Args:
        usuario_id: ID do usuário que tentou a ação
        tipo_tentativa: Tipo de tentativa ('acesso_admin', 'editar_outro_usuario', etc)
        ip: IP do usuário
        detalhes: Detalhes adicionais sobre a tentativa (opcional)
        alvo_user_id: ID do usuário alvo da tentativa (opcional)
        user_agent: User agent do navegador (opcional)
        bloqueado: Se a tentativa foi bloqueada (padrão True)
    
    Returns:
        ID do registro criado
    """
    try:
        # Buscar informações do usuário
        user_data = executar_query(
            "SELECT nome FROM usuarios WHERE id = ?",
            [usuario_id],
            fetch_one=True
        )
        usuario_nome = user_data['nome'] if user_data else 'Desconhecido'
        
        # Buscar informações do usuário alvo, se aplicável
        alvo_user_nome = None
        if alvo_user_id:
            alvo_data = executar_query(
                "SELECT nome FROM usuarios WHERE id = ?",
                [alvo_user_id],
                fetch_one=True
            )
            alvo_user_nome = alvo_data['nome'] if alvo_data else None
        
        # Inserir registro
        query = """
            INSERT INTO tentativas_acesso_nao_autorizado (
                usuario_id, usuario_nome, tipo_tentativa, detalhes,
                alvo_user_id, alvo_user_nome, ip, user_agent, bloqueado
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [
                usuario_id, usuario_nome, tipo_tentativa, detalhes,
                alvo_user_id, alvo_user_nome, ip, user_agent, 
                1 if bloqueado else 0
            ])
            tentativa_id = cursor.lastrowid
        
        security_logger.warning(
            f"Tentativa não autorizada registrada: {tipo_tentativa} por usuário {usuario_id} "
            f"({usuario_nome}) - ID: {tentativa_id} - Bloqueado: {bloqueado}"
        )
        return tentativa_id
        
    except Exception as e:
        logger.error(f"Erro ao gravar tentativa não autorizada: {e}", exc_info=True)
        return None


def criar_notificacao_usuario(usuario_id, tipo, titulo, mensagem, acao_url=None):
    """
    Cria uma notificação para o usuário.
    
    Args:
        usuario_id: ID do usuário que receberá a notificação
        tipo: Tipo de notificação ('senha_resetada', 'conta_inativada', etc)
        titulo: Título da notificação
        mensagem: Mensagem da notificação
        acao_url: URL de ação (opcional)
    
    Returns:
        ID da notificação criada
    """
    try:
        query = """
            INSERT INTO notificacoes_usuario (
                usuario_id, tipo, titulo, mensagem, acao_url
            ) VALUES (?, ?, ?, ?, ?)
        """
        
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, [usuario_id, tipo, titulo, mensagem, acao_url])
            notif_id = cursor.lastrowid
        
        logger.info(f"Notificação criada para usuário {usuario_id}: {tipo} - ID: {notif_id}")
        return notif_id
        
    except Exception as e:
        logger.error(f"Erro ao criar notificação: {e}", exc_info=True)
        return None


def obter_notificacoes_usuario(usuario_id, apenas_nao_lidas=False, limite=50):
    """
    Obtém as notificações de um usuário.
    
    Args:
        usuario_id: ID do usuário
        apenas_nao_lidas: Se True, retorna apenas notificações não lidas
        limite: Número máximo de notificações a retornar
    
    Returns:
        Lista de notificações
    """
    try:
        query = """
            SELECT * FROM notificacoes_usuario 
            WHERE usuario_id = ?
        """
        params = [usuario_id]
        
        if apenas_nao_lidas:
            query += " AND lida = 0"
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limite)
        
        return executar_query(query, params)
        
    except Exception as e:
        logger.error(f"Erro ao obter notificações: {e}", exc_info=True)
        return []


def marcar_notificacao_usuario_lida(notificacao_id, usuario_id):
    """
    Marca uma notificação de usuário (tabela notificacoes_usuario) como lida.
    NOTA: Esta função é distinta de marcar_notificacao_lida() que atua na tabela 'notificacoes'.
    
    Args:
        notificacao_id: ID da notificação
        usuario_id: ID do usuário (para validação)
    
    Returns:
        True se bem-sucedido, False caso contrário
    """
    try:
        query = """
            UPDATE notificacoes_usuario 
            SET lida = 1, 
                lida_em = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
            WHERE id = ? AND usuario_id = ?
        """
        
        executar_query(query, [notificacao_id, usuario_id])
        return True
        
    except Exception as e:
        logger.error(f"Erro ao marcar notificação de usuário como lida: {e}", exc_info=True)
        return False


def gerar_senha_temporaria(tamanho=12):
    """
    Gera uma senha temporária forte.
    
    Args:
        tamanho: Tamanho da senha (padrão 12)
    
    Returns:
        Senha temporária gerada
    """
    import string
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(tamanho))


def mascarar_email(email):
    """
    Mascara um email para exibição segura.
    
    Args:
        email: Email a ser mascarado
    
    Returns:
        Email mascarado (exemplo: m***@email.com)
    """
    if not email or '@' not in email:
        return email
    
    partes = email.split('@')
    usuario = partes[0]
    dominio = partes[1]
    
    if len(usuario) <= 2:
        usuario_mascarado = usuario[0] + '*'
    else:
        usuario_mascarado = usuario[0] + '***'
    
    return f"{usuario_mascarado}@{dominio}"


def obter_logs_auditoria(filtros=None, pagina=1, por_pagina=50):
    """
    Obtém logs de auditoria administrativa com filtros.
    
    Args:
        filtros: Dict com filtros (admin_id, acao, usuario_afetado_id, data_inicio, data_fim)
        pagina: Número da página
        por_pagina: Registros por página
    
    Returns:
        Dict com 'logs' e 'total'
    """
    try:
        query = "SELECT * FROM auditoria_admin WHERE 1=1"
        params = []
        
        if filtros:
            if filtros.get('admin_id'):
                query += " AND admin_id = ?"
                params.append(filtros['admin_id'])
            
            if filtros.get('acao'):
                query += " AND acao = ?"
                params.append(filtros['acao'])
            
            if filtros.get('usuario_afetado_id'):
                query += " AND usuario_afetado_id = ?"
                params.append(filtros['usuario_afetado_id'])
            
            if filtros.get('data_inicio'):
                query += " AND created_at >= ?"
                params.append(filtros['data_inicio'])
            
            if filtros.get('data_fim'):
                query += " AND created_at <= ?"
                params.append(filtros['data_fim'])
        
        # Contar total
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = executar_query(count_query, params, fetch_one=True)
        total = total['COUNT(*)'] if total else 0
        
        # Adicionar paginação
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([por_pagina, (pagina - 1) * por_pagina])
        
        logs = executar_query(query, params)
        
        return {
            'logs': logs,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': math.ceil(total / por_pagina) if total > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter logs de auditoria: {e}", exc_info=True)
        return {'logs': [], 'total': 0, 'pagina': 1, 'por_pagina': por_pagina, 'total_paginas': 0}
def obter_tema_usuario(usuario_id):
    """Retorna o tema de cor do usuário."""
    query = """
        SELECT tema_cor FROM user_preferences 
        WHERE usuario_id = ?
    """
    result = executar_query(query, [usuario_id], fetch_one=True)
    return result['tema_cor'] if result and result.get('tema_cor') else 'dourado'

def salvar_tema_usuario(usuario_id, tema_cor):
    """Salva o tema de cor do usuário."""
    query_check = "SELECT id FROM user_preferences WHERE usuario_id = ?"
    existe = executar_query(query_check, [usuario_id], fetch_one=True)
    
    if existe:
        query = """
            UPDATE user_preferences 
            SET tema_cor = ?, updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
            WHERE usuario_id = ?
        """
        return executar_query(query, [tema_cor, usuario_id])
    else:
        query = """
            INSERT INTO user_preferences (usuario_id, tema_cor)
            VALUES (?, ?)
        """
        return executar_query(query, [usuario_id, tema_cor])

def listar_apresentantes(filtros=None, pagina=1, registros_por_pagina=10):
    """Lista apresentantes com paginação e filtros."""
    import math
    offset = (pagina - 1) * registros_por_pagina
    
    query = """SELECT r.*,
               (SELECT COUNT(*) FROM processos pr
                  WHERE pr.apresentante_id = r.id
                     OR (pr.apresentante_id IS NULL AND pr.apresentante = r.nome)) as total_processos
               FROM apresentantes r WHERE 1=1"""
    params = []
    
    if filtros:
        if filtros.get('busca'):
            query += " AND (r.nome LIKE ? OR r.email LIKE ? OR r.telefone LIKE ?)"
            busca = f"%{filtros['busca']}%"
            params.extend([busca, busca, busca])
            
    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_records = executar_query(count_query, params, fetch_one=True)['COUNT(*)']
    
    ordenar = filtros.get('ordenar', 'nome') if filtros else 'nome'
    direcao = filtros.get('direcao', 'asc') if filtros else 'asc'
    
    colunas_validas = {'nome': 'r.nome', 'email': 'r.email', 'telefone': 'r.telefone', 'processos': 'total_processos'}
    col_sql = colunas_validas.get(ordenar, 'r.nome')
    dir_sql = 'DESC' if direcao == 'desc' else 'ASC'
    
    query += f" ORDER BY {col_sql} {dir_sql} LIMIT ? OFFSET ?"
    params.extend([registros_por_pagina, offset])
    
    apresentantes = executar_query(query, params, fetch_all=True)
    
    return {
        'apresentantes': apresentantes,
        'total_records': total_records,
        'total_pages': math.ceil(total_records / registros_por_pagina) if total_records > 0 else 0
    }

def get_apresentante_by_id(apresentante_id):
    """Obtém detalhes de um apresentante pelo ID."""
    query = """SELECT r.*,
               (SELECT COUNT(*) FROM processos pr
                  WHERE pr.apresentante_id = r.id
                     OR (pr.apresentante_id IS NULL AND pr.apresentante = r.nome)) as total_processos
               FROM apresentantes r WHERE r.id = ?"""
    return executar_query(query, [apresentante_id], fetch_one=True)

def apresentante_tem_processos(apresentante_id):
    """Verifica vínculo por ID e mantém fallback para processos legados."""
    rep = executar_query("SELECT nome FROM apresentantes WHERE id = ?", [apresentante_id], fetch_one=True)
    if not rep:
        return False
    result = executar_query(
        """
        SELECT COUNT(*) AS cnt
          FROM processos
         WHERE apresentante_id = ?
            OR (apresentante_id IS NULL AND apresentante = ?)
        """,
        [apresentante_id, rep['nome']],
        fetch_one=True,
    )
    return result['cnt'] > 0 if result else False

def editar_apresentante(apresentante_id, nome, telefone, email, connection=None, usuario_id=None):
    """Atualiza um apresentante e sincroniza os processos vinculados pelo nome."""
    from datetime import datetime

    if connection is None:
        with get_sqlite_connection() as conn:
            return editar_apresentante(apresentante_id, nome, telefone, email, connection=conn, usuario_id=usuario_id)

    apresentante_atual = executar_query(
        "SELECT nome, telefone, email FROM apresentantes WHERE id = ?",
        [apresentante_id],
        fetch_one=True,
        connection=connection,
    )
    if not apresentante_atual:
        return False

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    nome_anterior = apresentante_atual['nome']

    executar_query(
        "UPDATE apresentantes SET nome = ?, telefone = ?, email = ?, updated_at = ? WHERE id = ?",
        [nome, telefone, email, now, apresentante_id],
        connection=connection,
    )
    _sincronizar_processos_cadastro(
        cadastro_id=apresentante_id,
        nome_anterior=nome_anterior,
        nome_novo=nome,
        telefone_novo=telefone,
        email_novo=email,
        tipo_cadastro='apresentante',
        usuario_id=usuario_id,
        connection=connection,
    )
    return True

def excluir_apresentante(apresentante_id, connection=None):
    """Exclui um apresentante sem processos vinculados."""
    rows = executar_query("DELETE FROM apresentantes WHERE id = ?", [apresentante_id], connection=connection)
    return rows

def get_historico_servicos_apresentante(apresentante_id_ou_nome):
    """Obtém o histórico por apresentante_id, com fallback para processos legados."""
    if isinstance(apresentante_id_ou_nome, int):
        where_sql = "p.apresentante_id = ? OR (p.apresentante_id IS NULL AND p.apresentante = (SELECT nome FROM apresentantes WHERE id = ?))"
        params = [apresentante_id_ou_nome, apresentante_id_ou_nome]
    else:
        where_sql = "p.apresentante = ?"
        params = [apresentante_id_ou_nome]

    query = f"""
        SELECT p.*, ts.nome as tipo_servico_nome, sp.nome as status_nome, sp.hex_color
        FROM processos p
        JOIN tipos_servico ts ON p.tipo_id = ts.id
        JOIN status_processo sp ON p.status_id = sp.id
        WHERE {where_sql}
        ORDER BY p.data_entrada DESC
    """
    return executar_query(query, params, fetch_all=True)

def buscar_apresentantes_json(termo):
    """Busca apresentantes para o dropdown de pesquisa (AJAX). '%' lista todos."""
    if termo.strip() == '%':
        query = "SELECT id, nome, telefone, email FROM apresentantes ORDER BY nome ASC LIMIT 50"
        return executar_query(query, [], fetch_all=True)
    query = "SELECT id, nome, telefone, email FROM apresentantes WHERE nome LIKE ? OR email LIKE ? ORDER BY nome ASC LIMIT 20"
    like = f"%{termo}%"
    return executar_query(query, [like, like], fetch_all=True)

def upsert_apresentante_from_processo(apresentante_nome, telefone, email, processo_id, connection=None, nome_anterior=None, cadastro_id=None, usuario_id=None, processo_excluido_id=None):
    """Cria ou atualiza um apresentante sem duplicar quando um processo é renomeado."""
    from datetime import datetime
    if not apresentante_nome:
        return None
    if connection is None:
        with get_sqlite_connection() as conn:
            return upsert_apresentante_from_processo(
                apresentante_nome,
                telefone,
                email,
                processo_id,
                connection=conn,
                nome_anterior=nome_anterior,
                cadastro_id=cadastro_id,
                usuario_id=usuario_id,
                processo_excluido_id=processo_excluido_id,
            )
        
    # O ID é a identidade principal. Assim, editar nome, telefone ou e-mail
    # pelo processo altera o cadastro original, mesmo que o nome tenha mudado.
    apresentante = None
    if cadastro_id:
        apresentante = executar_query(
            "SELECT id, nome, telefone, email FROM apresentantes WHERE id = ?",
            [cadastro_id],
            fetch_one=True,
            connection=connection,
        )

    if apresentante is None:
        apresentante = executar_query(
            "SELECT id, nome, telefone, email FROM apresentantes WHERE nome = ?",
            [apresentante_nome],
            fetch_one=True,
            connection=connection,
        )
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if apresentante:
        apresentante_atual = executar_query("SELECT telefone, email FROM apresentantes WHERE id = ?", [apresentante['id']], fetch_one=True, connection=connection)
        
        novo_telefone = telefone if telefone else apresentante_atual['telefone']
        novo_email = email if email else apresentante_atual['email']
        
        query_update = """
            UPDATE apresentantes 
            SET telefone = ?, email = ?, updated_at = ? 
            WHERE id = ?
        """
        nome_atual = apresentante.get('nome') or apresentante_nome
        nome_final = apresentante_nome if cadastro_id else nome_atual
        executar_query(
            "UPDATE apresentantes SET nome = ?, telefone = ?, email = ?, updated_at = ? WHERE id = ?",
            [nome_final, novo_telefone, novo_email, now, apresentante['id']],
            connection=connection,
        )
        _sincronizar_processos_cadastro(
            cadastro_id=apresentante['id'],
            nome_anterior=nome_atual,
            nome_novo=nome_final,
            telefone_novo=novo_telefone,
            email_novo=novo_email,
            tipo_cadastro='apresentante',
            usuario_id=usuario_id,
            processo_excluido_id=processo_excluido_id,
            connection=connection,
        )
        return apresentante['id']
    else:
        if nome_anterior and nome_anterior != apresentante_nome:
            apresentante_anterior = executar_query(
                "SELECT id FROM apresentantes WHERE nome = ?",
                [nome_anterior],
                fetch_one=True,
                connection=connection,
            )
            if apresentante_anterior:
                total_processos = executar_query(
                    """
                    SELECT COUNT(*) AS total
                      FROM processos
                     WHERE apresentante_id = ?
                        OR (apresentante_id IS NULL AND apresentante = ?)
                    """,
                    [apresentante_anterior['id'], nome_anterior],
                    fetch_one=True,
                    connection=connection,
                )
                if total_processos and total_processos['total'] <= 1:
                    executar_query(
                        """
                        UPDATE apresentantes
                           SET nome = ?, telefone = ?, email = ?, updated_at = ?
                         WHERE id = ?
                        """,
                        [apresentante_nome, telefone, email, now, apresentante_anterior['id']],
                        connection=connection,
                    )
                    _sincronizar_processos_cadastro(
                        cadastro_id=apresentante_anterior['id'],
                        nome_anterior=nome_anterior,
                        nome_novo=apresentante_nome,
                        telefone_novo=telefone,
                        email_novo=email,
                        tipo_cadastro='apresentante',
                        usuario_id=usuario_id,
                        processo_excluido_id=processo_excluido_id,
                        connection=connection,
                    )
                    return apresentante_anterior['id']

        query_insert = """
            INSERT INTO apresentantes (nome, telefone, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = connection.cursor()
        cursor.execute(query_insert, [apresentante_nome, telefone, email, now, now])
        return cursor.lastrowid
