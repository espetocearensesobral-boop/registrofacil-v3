# routes/dashboard.py
# Dashboard com gráficos interativos e estatísticas

from flask import Blueprint, render_template, jsonify, session
from models import executar_query
from routes.auth import login_status_required
from routes.permissoes import permission_required
from utils.logger import operacional_logger as logger
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard_bp.route('/api/graficos', methods=['GET'])
@login_status_required
def api_graficos():
    """API que retorna dados para gráficos do dashboard."""
    try:
        usuario_id = session.get('usuario_id')
        
        # Gráfico 1: Processos por Status (Últimos 30 dias)
        query_status = """
            SELECT 
                s.nome as label,
                s.hex_color as color,
                COUNT(p.id) as value
            FROM processos p
            JOIN status_processo s ON p.status_id = s.id
            WHERE p.created_at >= date('now', 'localtime', '-30 days')
            GROUP BY s.id, s.nome, s.hex_color
            ORDER BY value DESC
        """
        dados_status = executar_query(query_status, fetch_all=True) or []
        
        # Gráfico 2: Timeline de Criação (Últimos 30 dias)
        query_timeline = """
            SELECT 
                DATE(created_at) as label,
                COUNT(*) as value
            FROM processos
            WHERE created_at >= date('now', 'localtime', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY label ASC
        """
        dados_timeline = executar_query(query_timeline, fetch_all=True) or []
        
        # Gráfico 3: Top 5 Tipos de Serviço
        query_tipos = """
            SELECT 
                t.nome as label,
                COUNT(p.id) as value
            FROM processos p
            JOIN tipos_servico t ON p.tipo_id = t.id
            WHERE p.created_at >= date('now', 'localtime', '-30 days')
            GROUP BY t.id, t.nome
            ORDER BY value DESC
            LIMIT 5
        """
        dados_tipos = executar_query(query_tipos, fetch_all=True) or []
        
        # Gráfico 4: Processos por Responsável (apenas ativos)
        query_responsaveis = """
            SELECT 
                COALESCE(u.nome, 'Sem Responsável') as label,
                COUNT(p.id) as value
            FROM processos p
            LEFT JOIN usuarios u ON p.responsavel_id = u.id
            WHERE p.data_conclusao IS NULL
            GROUP BY u.id, u.nome
            ORDER BY value DESC
            LIMIT 10
        """
        dados_responsaveis = executar_query(query_responsaveis, fetch_all=True) or []
        
        # Gráfico 5: Processos Vencidos vs Em Dia
        total_processos = executar_query(
            "SELECT COUNT(*) as total FROM processos WHERE data_conclusao IS NULL",
            fetch_one=True
        )
        total_processos = total_processos['total'] if total_processos else 0
        
        vencidos = executar_query(
            "SELECT COUNT(*) as total FROM processos WHERE prazo_final < date('now') AND data_conclusao IS NULL",
            fetch_one=True
        )
        vencidos = vencidos['total'] if vencidos else 0
        
        em_dia = total_processos - vencidos
        
        dados_prazo = [
            {'label': 'Vencidos', 'value': vencidos, 'color': '#dc3545'},
            {'label': 'Em Dia', 'value': em_dia, 'color': '#28a745'}
        ]
        
        # Gráfico 6: Evolução Mensal (Últimos 6 meses)
        query_mensal = """
            SELECT 
                strftime('%Y-%m', created_at) as mes,
                COUNT(*) as criados,
                SUM(CASE WHEN data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos
            FROM processos
            WHERE created_at >= date('now', 'localtime', '-6 months')
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY mes ASC
        """
        dados_mensal = executar_query(query_mensal, fetch_all=True) or []
        
        # Estatísticas resumidas
        query_stats = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN data_conclusao IS NULL THEN 1 ELSE 0 END) as ativos,
                SUM(CASE WHEN data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos,
                SUM(CASE WHEN prazo_final < date('now') AND data_conclusao IS NULL THEN 1 ELSE 0 END) as vencidos
            FROM processos
        """
        stats = executar_query(query_stats, fetch_one=True) or {
            'total': 0, 'ativos': 0, 'concluidos': 0, 'vencidos': 0
        }
        
        return jsonify({
            'success': True,
            'graficos': {
                'status': dados_status,
                'timeline': dados_timeline,
                'tipos': dados_tipos,
                'responsaveis': dados_responsaveis,
                'prazo': dados_prazo,
                'mensal': dados_mensal
            },
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados dos gráficos: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao carregar dados dos gráficos'
        }), 500


@dashboard_bp.route('/api/stats/resumo', methods=['GET'])
@login_status_required
def api_stats_resumo():
    """Retorna estatísticas resumidas em tempo real."""
    try:
        stats = {}
        
        # Processos hoje
        stats['hoje'] = executar_query(
            "SELECT COUNT(*) as total FROM processos WHERE DATE(created_at) = DATE('now', 'localtime')",
            fetch_one=True
        )['total']
        
        # Processos esta semana
        stats['semana'] = executar_query(
            "SELECT COUNT(*) as total FROM processos WHERE created_at >= date('now', 'localtime', 'weekday 0', '-7 days')",
            fetch_one=True
        )['total']
        
        # Processos este mês
        stats['mes'] = executar_query(
            "SELECT COUNT(*) as total FROM processos WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')",
            fetch_one=True
        )['total']
        
        # Tempo médio de conclusão (em dias)
        query_tempo_medio = """
            SELECT 
                AVG(julianday(data_conclusao) - julianday(created_at)) as media_dias
            FROM processos
            WHERE data_conclusao IS NOT NULL
            AND created_at >= date('now', '-30 days')
        """
        tempo_medio = executar_query(query_tempo_medio, fetch_one=True)
        stats['tempo_medio_conclusao'] = round(tempo_medio['media_dias'], 1) if tempo_medio and tempo_medio['media_dias'] else 0
        
        # Taxa de conclusão no prazo
        query_taxa = """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN data_conclusao <= prazo_final THEN 1 ELSE 0 END) as no_prazo
            FROM processos
            WHERE data_conclusao IS NOT NULL
            AND created_at >= date('now', '-30 days')
        """
        taxa = executar_query(query_taxa, fetch_one=True)
        if taxa and taxa['total'] > 0:
            stats['taxa_no_prazo'] = round((taxa['no_prazo'] / taxa['total']) * 100, 1)
        else:
            stats['taxa_no_prazo'] = 0
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas resumidas: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao carregar estatísticas'
        }), 500


@dashboard_bp.route('/api/stats/performance', methods=['GET'])
@login_status_required
def api_stats_performance():
    """Retorna métricas de performance da equipe."""
    try:
        # Performance por usuário (últimos 30 dias)
        query_performance = """
            SELECT 
                u.nome as usuario,
                COUNT(p.id) as total_processos,
                SUM(CASE WHEN p.data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos,
                SUM(CASE WHEN p.prazo_final < date('now') AND p.data_conclusao IS NULL THEN 1 ELSE 0 END) as vencidos,
                AVG(CASE WHEN p.data_conclusao IS NOT NULL 
                    THEN julianday(p.data_conclusao) - julianday(p.created_at) 
                    ELSE NULL END) as tempo_medio
            FROM usuarios u
            LEFT JOIN processos p ON u.id = p.responsavel_id 
                AND p.created_at >= date('now', 'localtime', '-30 days')
            WHERE u.ativo = 1
            GROUP BY u.id, u.nome
            HAVING COUNT(p.id) > 0
            ORDER BY concluidos DESC, total_processos DESC
        """
        performance = executar_query(query_performance, fetch_all=True) or []
        
        # Formatar dados
        for item in performance:
            if item['tempo_medio']:
                item['tempo_medio'] = round(item['tempo_medio'], 1)
            if item['total_processos'] > 0:
                item['taxa_conclusao'] = round((item['concluidos'] / item['total_processos']) * 100, 1)
            else:
                item['taxa_conclusao'] = 0
        
        return jsonify({
            'success': True,
            'performance': performance
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar performance: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': 'Erro ao carregar métricas de performance'
        }), 500


@dashboard_bp.route('/metricas', methods=['GET'])
@login_status_required
@permission_required('metricas_visualizar')
def metricas():
    """Página de métricas e análises detalhadas."""
    usuario_id = session.get('usuario_id')
    usuario_nome = session.get('usuario_nome', 'Usuário')
    
    return render_template('metricas.html',
                         usuario_id=usuario_id,
                         usuario_nome=usuario_nome)


@dashboard_bp.route('/api/metricas/usuario', methods=['GET'])
@login_status_required
def api_metricas_usuario():
    """Retorna métricas detalhadas do usuário logado."""
    try:
        usuario_id = session.get('usuario_id')
        
        # KPIs Principais do Usuário
        query_kpis = """
            SELECT 
                COUNT(*) as total_processos,
                SUM(CASE WHEN data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos,
                SUM(CASE WHEN data_conclusao IS NULL THEN 1 ELSE 0 END) as em_andamento,
                SUM(CASE WHEN prazo_final < date('now') AND data_conclusao IS NULL THEN 1 ELSE 0 END) as atrasados,
                AVG(CASE WHEN data_conclusao IS NOT NULL 
                    THEN julianday(data_conclusao) - julianday(created_at) END) as tempo_medio_dias,
                SUM(CASE WHEN data_conclusao IS NOT NULL AND data_conclusao <= prazo_final THEN 1 ELSE 0 END) as concluidos_no_prazo
            FROM processos
            WHERE responsavel_id = ?
            
        """
        kpis = executar_query(query_kpis, [usuario_id], fetch_one=True)
        
        # Garantir que kpis seja um dicionário válido
        if not kpis or not isinstance(kpis, dict):
            kpis = {
                'total_processos': 0,
                'concluidos': 0,
                'em_andamento': 0,
                'atrasados': 0,
                'tempo_medio_dias': 0,
                'concluidos_no_prazo': 0
            }
        
        # Calcular métricas derivadas com validação
        total = kpis.get('total_processos', 0) or 0
        concluidos = kpis.get('concluidos', 0) or 0
        concluidos_prazo = kpis.get('concluidos_no_prazo', 0) or 0
        atrasados = kpis.get('atrasados', 0) or 0
        
        kpis['taxa_conclusao'] = round((concluidos / total * 100), 1) if total > 0 else 0
        kpis['taxa_prazo'] = round((concluidos_prazo / concluidos * 100), 1) if concluidos > 0 else 0
        kpis['taxa_atraso'] = round((atrasados / total * 100), 1) if total > 0 else 0
        kpis['tempo_medio_dias'] = round(kpis.get('tempo_medio_dias', 0) or 0, 1)
        
        # Evolução nos últimos 30 dias (por dia)
        query_evolucao = """
            SELECT 
                DATE(created_at) as data,
                COUNT(*) as criados,
                SUM(CASE WHEN data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos
            FROM processos
            WHERE responsavel_id = ?
            AND created_at >= date('now', 'localtime', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY data ASC
        """
        evolucao = executar_query(query_evolucao, [usuario_id], fetch_all=True) or []
        
        # Processos por Status
        query_status = """
            SELECT 
                s.nome as status,
                s.hex_color as cor,
                COUNT(p.id) as quantidade
            FROM processos p
            JOIN status_processo s ON p.status_id = s.id
            WHERE p.responsavel_id = ?
            AND p.data_conclusao IS NULL
            GROUP BY s.id, s.nome, s.hex_color
            ORDER BY quantidade DESC
        """
        por_status = executar_query(query_status, [usuario_id], fetch_all=True) or []
        
        # Processos por Tipo de Serviço
        query_tipos = """
            SELECT 
                t.nome as tipo,
                COUNT(p.id) as quantidade,
                SUM(CASE WHEN p.data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos
            FROM processos p
            JOIN tipos_servico t ON p.tipo_id = t.id
            WHERE p.responsavel_id = ?
            
            GROUP BY t.id, t.nome
            ORDER BY quantidade DESC
            LIMIT 10
        """
        por_tipo = executar_query(query_tipos, [usuario_id], fetch_all=True) or []
        
        # Performance Semanal (últimas 8 semanas)
        query_semanal = """
            SELECT 
                strftime('%Y-%W', created_at) as semana,
                COUNT(*) as total,
                SUM(CASE WHEN data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos,
                AVG(CASE WHEN data_conclusao IS NOT NULL 
                    THEN julianday(data_conclusao) - julianday(created_at) END) as tempo_medio
            FROM processos
            WHERE responsavel_id = ?
            AND created_at >= date('now', 'localtime', '-56 days')
            GROUP BY strftime('%Y-%W', created_at)
            ORDER BY semana ASC
        """
        performance_semanal = executar_query(query_semanal, [usuario_id], fetch_all=True) or []
        
        # Comparativo com a equipe
        # Nota: executar_query detecta SELECT pelo início da query; usamos subconsulta aninhada
        # para evitar CTE (WITH ...) que começa com WITH e não é reconhecida como SELECT.
        query_comparativo = """
            SELECT 
                u.processos as meus_processos,
                u.concluidos as meus_concluidos,
                u.tempo_medio as meu_tempo_medio,
                e.media_processos,
                e.media_concluidos,
                e.media_tempo as media_tempo_equipe
            FROM (
                SELECT 
                    COUNT(*) as processos,
                    SUM(CASE WHEN data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos,
                    AVG(CASE WHEN data_conclusao IS NOT NULL 
                        THEN julianday(data_conclusao) - julianday(created_at) END) as tempo_medio
                FROM processos
                WHERE responsavel_id = ?
                AND created_at >= date('now', '-30 days')
            ) u, (
                SELECT 
                    AVG(processos_count) as media_processos,
                    AVG(concluidos_count) as media_concluidos,
                    AVG(tempo_medio) as media_tempo
                FROM (
                    SELECT 
                        COUNT(*) as processos_count,
                        SUM(CASE WHEN data_conclusao IS NOT NULL THEN 1 ELSE 0 END) as concluidos_count,
                        AVG(CASE WHEN data_conclusao IS NOT NULL 
                            THEN julianday(data_conclusao) - julianday(created_at) END) as tempo_medio
                    FROM processos
                    WHERE created_at >= date('now', 'localtime', '-30 days')
                    GROUP BY responsavel_id
                )
            ) e
        """
        comparativo = executar_query(query_comparativo, [usuario_id], fetch_one=True)
        
        # Garantir que comparativo seja um dicionário válido
        if not comparativo or not isinstance(comparativo, dict):
            comparativo = {
                'meus_processos': 0,
                'meus_concluidos': 0,
                'meu_tempo_medio': 0,
                'media_processos': 0,
                'media_concluidos': 0,
                'media_tempo_equipe': 0,
                'perf_volume': 0,
                'perf_conclusao': 0,
                'perf_velocidade': 0
            }
        else:
            # Calcular percentuais de performance
            comparativo['meu_tempo_medio'] = round(comparativo.get('meu_tempo_medio', 0) or 0, 1)
            comparativo['media_tempo_equipe'] = round(comparativo.get('media_tempo_equipe', 0) or 0, 1)
            comparativo['media_processos'] = round(comparativo.get('media_processos', 0) or 0, 1)
            comparativo['media_concluidos'] = round(comparativo.get('media_concluidos', 0) or 0, 1)
            
            # Performance relativa (% comparado à média)
            meus_proc = comparativo.get('meus_processos', 0) or 0
            media_proc = comparativo.get('media_processos', 0) or 0
            
            if media_proc > 0:
                comparativo['perf_volume'] = round((meus_proc / media_proc * 100) - 100, 1)
            else:
                comparativo['perf_volume'] = 0
            
            meus_concl = comparativo.get('meus_concluidos', 0) or 0
            media_concl = comparativo.get('media_concluidos', 0) or 0
            
            if media_concl > 0:
                comparativo['perf_conclusao'] = round((meus_concl / media_concl * 100) - 100, 1)
            else:
                comparativo['perf_conclusao'] = 0
            
            meu_tempo = comparativo.get('meu_tempo_medio', 0) or 0
            media_tempo = comparativo.get('media_tempo_equipe', 0) or 0
            
            if media_tempo > 0 and meu_tempo > 0:
                # Tempo menor é melhor, então invertemos a lógica
                comparativo['perf_velocidade'] = round((media_tempo / meu_tempo * 100) - 100, 1)
            else:
                comparativo['perf_velocidade'] = 0
        
        return jsonify({
            'success': True,
            'kpis': kpis,
            'evolucao': evolucao,
            'por_status': por_status,
            'por_tipo': por_tipo,
            'performance_semanal': performance_semanal,
            'comparativo': comparativo
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar métricas do usuário: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
