# routes/notificacoes.py
# Sistema de notificações push para alertas de prazos e eventos

from flask import Blueprint, jsonify, session, request
from models import (executar_query, criar_notificacao, listar_notificacoes_pendentes,
                    marcar_notificacao_lida, marcar_todas_lidas)
from routes.auth import login_status_required
from utils.logger import logger
from datetime import datetime

notificacoes_bp = Blueprint('notificacoes', __name__, url_prefix='/notificacoes')


@notificacoes_bp.route('/api/pendentes', methods=['GET'])
@login_status_required
def api_pendentes():
    """Retorna notificações pendentes para o usuário."""
    try:
        usuario_id = session.get('usuario_id')
        
        # Buscar notificações não lidas
        notificacoes_db = listar_notificacoes_pendentes(usuario_id, limit=50)
        
        # Também verificar processos vencendo/vencidos em tempo real
        notificacoes_dinamicas = []
        
        # Processos vencendo em 24h
        query_vencendo = """
            SELECT id, numero_processo, titular, prazo_final
            FROM processos
            WHERE responsavel_id = ?
            AND data_conclusao IS NULL
            AND prazo_final BETWEEN date('now') AND date('now', '+1 day')
        """
        vencendo = executar_query(query_vencendo, [usuario_id], fetch_all=True) or []
        
        for proc in vencendo:
            notificacoes_dinamicas.append({
                'id': f'prazo_vencendo_{proc["id"]}',
                'tipo': 'prazo_vencendo',
                'titulo': '⏰ Prazo Vencendo em 24h!',
                'mensagem': f'Processo {proc["numero_processo"]} - {proc["titular"]} vence em {proc["prazo_final"]}',
                'url': f'/processos/visualizar/processo={proc["id"]}',
                'prioridade': 'alta',
                'processo_id': proc['id'],
                'lida': False
            })
        
        # Processos já vencidos
        query_vencidos = """
            SELECT id, numero_processo, titular, prazo_final
            FROM processos
            WHERE responsavel_id = ?
            AND data_conclusao IS NULL
            AND prazo_final < date('now')
            ORDER BY prazo_final ASC
            LIMIT 10
        """
        vencidos = executar_query(query_vencidos, [usuario_id], fetch_all=True) or []
        
        for proc in vencidos:
            dias_atraso = executar_query(
                "SELECT julianday('now') - julianday(?) as dias",
                [proc['prazo_final']],
                fetch_one=True
            )['dias']
            
            notificacoes_dinamicas.append({
                'id': f'prazo_vencido_{proc["id"]}',
                'tipo': 'prazo_vencido',
                'titulo': '🚨 Prazo Vencido!',
                'mensagem': f'Processo {proc["numero_processo"]} - {proc["titular"]} está {int(dias_atraso)} dia(s) atrasado',
                'url': f'/processos/visualizar/processo={proc["id"]}',
                'prioridade': 'alta',
                'processo_id': proc['id'],
                'lida': False
            })
        
        # Combinar notificações do banco e dinâmicas
        todas_notificacoes = list(notificacoes_db) + notificacoes_dinamicas
        
        # Ordenar por prioridade e data
        def sort_key(n):
            prioridade_ordem = {'alta': 0, 'media': 1, 'normal': 2, 'baixa': 3}
            return (
                prioridade_ordem.get(n.get('prioridade', 'normal'), 2),
                n.get('created_at', datetime.now().isoformat())
            )
        
        todas_notificacoes.sort(key=sort_key)
        
        return jsonify({
            'success': True,
            'notificacoes': todas_notificacoes,
            'total': len(todas_notificacoes),
            'nao_lidas': len([n for n in todas_notificacoes if not n.get('lida', False)])
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar notificações pendentes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao carregar notificações'
        }), 500


@notificacoes_bp.route('/api/<int:notificacao_id>/marcar-lida', methods=['POST'])
@login_status_required
def api_marcar_lida(notificacao_id):
    """Marca uma notificação como lida."""
    try:
        usuario_id = session.get('usuario_id')
        resultado = marcar_notificacao_lida(notificacao_id, usuario_id)
        
        return jsonify({
            'success': True if resultado else False,
            'message': 'Notificação marcada como lida' if resultado else 'Notificação não encontrada'
        })
        
    except Exception as e:
        logger.error(f"Erro ao marcar notificação como lida: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao atualizar notificação'
        }), 500


@notificacoes_bp.route('/api/marcar-todas-lidas', methods=['POST'])
@login_status_required
def api_marcar_todas_lidas():
    """Marca todas as notificações do usuário como lidas."""
    try:
        usuario_id = session.get('usuario_id')
        resultado = marcar_todas_lidas(usuario_id)
        
        return jsonify({
            'success': True,
            'message': 'Todas as notificações foram marcadas como lidas'
        })
        
    except Exception as e:
        logger.error(f"Erro ao marcar todas notificações como lidas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao atualizar notificações'
        }), 500


@notificacoes_bp.route('/api/criar', methods=['POST'])
@login_status_required
def api_criar_notificacao():
    """Cria uma nova notificação (admin/sistema)."""
    try:
        usuario_id = session.get('usuario_id')
        data = request.get_json()
        
        # Verificar se usuário tem permissão (admin)
        user = executar_query(
            "SELECT role FROM usuarios WHERE id = ?",
            [usuario_id],
            fetch_one=True
        )
        
        if not user or user['role'] != 'admin':
            return jsonify({
                'success': False,
                'message': 'Sem permissão para criar notificações'
            }), 403
        
        # Validar dados
        campos_obrigatorios = ['usuario_destino_id', 'tipo', 'titulo', 'mensagem']
        for campo in campos_obrigatorios:
            if not data.get(campo):
                return jsonify({
                    'success': False,
                    'message': f'Campo obrigatório: {campo}'
                }), 400
        
        # Criar notificação
        resultado = criar_notificacao(
            usuario_id=data['usuario_destino_id'],
            tipo=data['tipo'],
            titulo=data['titulo'],
            mensagem=data['mensagem'],
            processo_id=data.get('processo_id'),
            url=data.get('url'),
            prioridade=data.get('prioridade', 'normal')
        )
        
        return jsonify({
            'success': True if resultado else False,
            'message': 'Notificação criada com sucesso' if resultado else 'Erro ao criar notificação'
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar notificação: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao criar notificação'
        }), 500


@notificacoes_bp.route('/api/stats', methods=['GET'])
@login_status_required
def api_stats_notificacoes():
    """Retorna estatísticas de notificações do usuário."""
    try:
        usuario_id = session.get('usuario_id')
        
        # Total de notificações
        total = executar_query(
            "SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = ?",
            [usuario_id],
            fetch_one=True
        )['total']
        
        # Não lidas
        nao_lidas = executar_query(
            "SELECT COUNT(*) as total FROM notificacoes WHERE usuario_id = ? AND lida = 0",
            [usuario_id],
            fetch_one=True
        )['total']
        
        # Por tipo
        por_tipo = executar_query(
            """
            SELECT tipo, COUNT(*) as total
            FROM notificacoes
            WHERE usuario_id = ?
            GROUP BY tipo
            ORDER BY total DESC
            """,
            [usuario_id],
            fetch_all=True
        ) or []
        
        # Por prioridade (não lidas)
        por_prioridade = executar_query(
            """
            SELECT prioridade, COUNT(*) as total
            FROM notificacoes
            WHERE usuario_id = ? AND lida = 0
            GROUP BY prioridade
            """,
            [usuario_id],
            fetch_all=True
        ) or []
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'nao_lidas': nao_lidas,
                'lidas': total - nao_lidas,
                'por_tipo': por_tipo,
                'por_prioridade': por_prioridade
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas de notificações: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao carregar estatísticas'
        }), 500


@notificacoes_bp.route('/api/configuracoes', methods=['GET', 'POST'])
@login_status_required
def api_configuracoes():
    """Obtém ou atualiza configurações de notificações do usuário."""
    try:
        usuario_id = session.get('usuario_id')
        
        if request.method == 'GET':
            # Buscar preferências
            from models import obter_preferencias_usuario
            prefs = obter_preferencias_usuario(usuario_id)
            
            return jsonify({
                'success': True,
                'configuracoes': {
                    'notificacoes_push': prefs.get('notificacoes_push', 1),
                    'notificacoes_email': prefs.get('notificacoes_email', 1)
                }
            })
        
        else:  # POST
            data = request.get_json()
            from models import atualizar_preferencias_usuario
            
            resultado = atualizar_preferencias_usuario(usuario_id, {
                'notificacoes_push': data.get('notificacoes_push', 1),
                'notificacoes_email': data.get('notificacoes_email', 1)
            })
            
            return jsonify({
                'success': True if resultado else False,
                'message': 'Configurações atualizadas' if resultado else 'Erro ao atualizar'
            })
        
    except Exception as e:
        logger.error(f"Erro ao processar configurações: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao processar configurações'
        }), 500
