"""Serviços de usuários, autenticação e auditoria.

As funções preservam as assinaturas legadas para que as rotas existentes
continuem importando-as através de `models.py`.
"""

from datetime import datetime, timedelta
import secrets
import sqlite3

import pytz

from config import Config
from data.database import executar_query, get_sqlite_connection
from utils.logger import logger, security_logger

TENTATIVAS_MAX = Config.TENTATIVAS_MAX
BLOQUEIO_TEMPO = Config.BLOQUEIO_TEMPO
VALID_USER_ROLES = frozenset({'admin', 'suporte', 'user'})

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

def _select_user_query(where_clause):
    return (
        "SELECT id, nome, email, usuario, senha, ativo, role, "
        "created_at, updated_at, deleted_at, last_login_at, session_invalidate_at, "
        "session_epoch, must_change_password FROM usuarios " + where_clause
    )


def get_user_by_username(username):
    try:
        return executar_query(
            _select_user_query("WHERE usuario = ?"),
            [username],
            fetch_one=True
        )
    except sqlite3.OperationalError as e:
        if "no such column: session_epoch" in str(e) or "no such column: session_invalidate_at" in str(e):
            logger.warning("Coluna de sessão ausente durante migração; usando consulta compatível.")
            return executar_query(
                "SELECT id, nome, email, usuario, senha, ativo, role, "
                "created_at, updated_at, deleted_at, last_login_at, session_invalidate_at, "
                "must_change_password FROM usuarios WHERE usuario = ?",
                [username],
                fetch_one=True
            )
        raise


def get_user_by_id(user_id):
    """Busca um usuário pelo ID com campos necessários ao guard de sessão."""
    try:
        return executar_query(_select_user_query("WHERE id = ?"), [user_id], fetch_one=True)
    except sqlite3.OperationalError as e:
        if "no such column: session_epoch" in str(e) or "no such column: session_invalidate_at" in str(e):
            return executar_query(
                "SELECT id, nome, email, usuario, senha, ativo, role, "
                "created_at, updated_at, deleted_at, last_login_at, session_invalidate_at, "
                "must_change_password FROM usuarios WHERE id = ?",
                [user_id], fetch_one=True
            )
        raise


def bump_user_session_epoch(user_id, connection=None):
    """Revoga todas as sessões do usuário de forma atômica."""
    query = (
        "UPDATE usuarios SET session_epoch = COALESCE(session_epoch, 0) + 1, "
        "session_invalidate_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), "
        "updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?"
    )
    try:
        return executar_query(query, [user_id], connection=connection)
    except sqlite3.OperationalError as e:
        if "no such column: session_epoch" in str(e):
            # Compatibilidade temporária para uma instalação que ainda não executou init_db.
            return executar_query(
                "UPDATE usuarios SET session_invalidate_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), "
                "updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?",
                [user_id], connection=connection
            )
        raise

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
    Cria um novo usuário no sistema e concede permissões básicas.
    """
    try:
        if role not in VALID_USER_ROLES:
            logger.warning(f"Tentativa de criar usuário com role inválida: {role!r}")
            return None

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

def create_password_reset_token(user_id, expires_in_minutes=60):
    # token: segredo completo, nunca exposto na URL
    token = secrets.token_urlsafe(64)
    # short_id: identificador público curto e opaco para a URL (ex: aB3xK9mQ)
    short_id = secrets.token_urlsafe(8)

    expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
    expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Um novo pedido revoga links anteriores ainda não utilizados.
        executar_query(
            "DELETE FROM password_reset_tokens WHERE user_id = ? AND is_used = 0",
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

