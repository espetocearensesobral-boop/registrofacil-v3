"""Operações de backup, manutenção, reconstrução e FTS."""

import os
import sqlite3
from datetime import datetime

from config import Config
from data.database import executar_query, get_sqlite_connection
from utils.logger import logger

DATABASE_PATH = Config.DATABASE_PATH
UPLOAD_FOLDER = Config.UPLOAD_PROCESSOS_DIR

def _init_db_compat():
    """Chama a fachada legada sem criar dependência circular no import."""
    from models import init_db
    return init_db()

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
            _init_db_compat()
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

