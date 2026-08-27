"""Infraestrutura compartilhada de acesso ao SQLite.

Este módulo contém apenas primitivas de persistência. A camada legada
(models.py) continua reexportando essas funções para manter compatibilidade
com as rotas e utilitários existentes.
"""

import sqlite3
from contextlib import contextmanager

from config import Config
from utils.logger import sistema_logger as logger

DATABASE_PATH = Config.DATABASE_PATH


@contextmanager
def get_sqlite_connection():
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
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
            results = cursor.fetchall()
            return [dict(row) for row in results]

        if close_conn:
            conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        logger.error(
            f"Erro no banco de dados SQLite durante a operação parametrizada: {e}",
            extra={'details': {'operation': 'executar_query'}},
            exc_info=True,
        )
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
    """Adiciona uma coluna SQLite caso ela ainda não exista."""
    with get_sqlite_connection() as temp_conn:
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute(f"PRAGMA table_info({table_name});")
        columns = [info[1] for info in temp_cursor.fetchall()]

    if column_name in columns:
        return

    if default_value and isinstance(default_value, str) and (
        default_value.startswith("strftime(")
        or default_value.upper() == 'CURRENT_TIMESTAMP'
        or default_value.upper() == 'CURRENT_DATE'
        or default_value.upper() == 'CURRENT_TIME'
    ):
        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        try:
            with get_sqlite_connection() as conn_for_alter:
                cursor_for_alter = conn_for_alter.cursor()
                cursor_for_alter.execute(alter_sql)
                logger.info(
                    f"Coluna '{column_name}' adicionada à tabela '{table_name}' sem valor padrão inicial."
                )
                update_sql = (
                    f"UPDATE {table_name} SET {column_name} = {default_value} "
                    f"WHERE {column_name} IS NULL;"
                )
                cursor_for_alter.execute(update_sql)
                logger.info(
                    f"Valores existentes na coluna '{column_name}' atualizados com '{default_value}'."
                )
        except sqlite3.OperationalError as e:
            logger.error(
                f"Erro operacional SQLite ao adicionar ou atualizar coluna "
                f"'{column_name}' à tabela '{table_name}': {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Erro inesperado ao adicionar ou atualizar coluna "
                f"'{column_name}' à tabela '{table_name}': {e}",
                exc_info=True,
            )
            raise
        return

    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
    if default_value is not None:
        if column_type.upper() == 'TEXT':
            alter_sql += f" DEFAULT '{default_value}'"
        else:
            alter_sql += f" DEFAULT {default_value}"

    try:
        with get_sqlite_connection() as conn_for_alter:
            cursor_for_alter = conn_for_alter.cursor()
            cursor_for_alter.execute(alter_sql)
            logger.info(
                f"Coluna '{column_name}' adicionada à tabela '{table_name}' com valor padrão."
            )
    except sqlite3.OperationalError as e:
        logger.error(
            f"Erro operacional SQLite ao adicionar coluna '{column_name}' "
            f"à tabela '{table_name}': {e}",
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            f"Erro inesperado ao adicionar coluna '{column_name}' "
            f"à tabela '{table_name}': {e}",
            exc_info=True,
        )
        raise
