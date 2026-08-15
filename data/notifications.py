"""Serviços de notificações e preferências do usuário."""

from data.database import executar_query, get_sqlite_connection
from utils.logger import logger

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
    
    campos_permitidos = ['tema', 'sidebar_selection_color', 'notificacoes_push', 'notificacoes_email',
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

def obter_preferencia_visual_usuario(usuario_id):
    """Retorna o tema institucional e a seleção da sidebar do usuário."""
    query = """
        SELECT tema_cor, sidebar_selection_color FROM user_preferences
        WHERE usuario_id = ?
    """
    result = executar_query(query, [usuario_id], fetch_one=True)
    return {
        'tema_cor': result.get('tema_cor') if result else 'paleta-01',
        'sidebar_selection_color': result.get('sidebar_selection_color') if result else '#1B4368',
    }


def obter_tema_usuario(usuario_id):
    """Compatibilidade: retorna somente uma das três Paletas institucionais."""
    return obter_preferencia_visual_usuario(usuario_id)['tema_cor'] or 'paleta-01'


def salvar_tema_usuario(usuario_id, tema_cor):
    """Salva uma Paleta institucional por usuário."""
    query = """
        INSERT INTO user_preferences (usuario_id, tema_cor, sidebar_selection_color)
        VALUES (?, ?, '#1B4368')
        ON CONFLICT(usuario_id) DO UPDATE SET
            tema_cor = excluded.tema_cor,
            updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
    """
    return executar_query(query, [usuario_id, tema_cor])


def salvar_cor_sidebar_usuario(usuario_id, sidebar_selection_color):
    """Salva somente a cor de destaque dos itens da sidebar."""
    query = """
        INSERT INTO user_preferences (usuario_id, tema_cor, sidebar_selection_color)
        VALUES (?, 'paleta-01', ?)
        ON CONFLICT(usuario_id) DO UPDATE SET
            sidebar_selection_color = excluded.sidebar_selection_color,
            updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
    """
    return executar_query(query, [usuario_id, sidebar_selection_color])
