"""Locks cooperativos de registros."""

import sqlite3
from datetime import datetime, timedelta

from data.database import executar_query, get_sqlite_connection
from utils.logger import logger

LOCK_TIMEOUT_MINUTES = 15

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
            return {'error': 'Não foi possível bloquear este registro agora. Atualize a página e tente novamente.', 'type': 'danger', 'code': 500}

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
        return {'success': False, 'error': 'Não foi possível liberar o bloqueio agora. Tente novamente.'}

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

