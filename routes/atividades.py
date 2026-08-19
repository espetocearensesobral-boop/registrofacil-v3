# registrofacil/routes/atividades.py

from flask import Blueprint, render_template, request, session, redirect, url_for, flash
import functools
from datetime import datetime, timedelta

from models import executar_query, gravar_log
from routes.auth import is_logged_in_status, login_status_required, get_client_ip, proteger_input
from routes.permissoes import permission_required
from utils.logger import operacional_logger as logger
from utils.helpers import formatar_data # Importar de utils.helpers
from data.audit_logs import obter_logs_seguranca

atividades_bp = Blueprint('atividades', __name__, url_prefix='/atividades')

@atividades_bp.route('/historico', methods=['GET'])
@login_status_required
@permission_required('atividades_visualizar')
def historico():
    usuario_id = session.get('usuario_id')
    ip = get_client_ip()
    logger.info(f"Acessando histórico de atividades. Usuário ID: {usuario_id}, IP: {ip}")

    pagina_atual = request.args.get('pagina', 1, type=int)
    filtro_usuario_id = request.args.get('usuario', type=int)
    filtro_acao = proteger_input(request.args.get('acao'))
    filtro_data = request.args.get('data')
    itens_por_pagina = request.args.get('itens_por_pagina', 50, type=int)
    ordenar = request.args.get('ordenar', 'created_at_desc')

    if not (1 <= itens_por_pagina <= 100):
        itens_por_pagina = 50
        flash("Lote de registros inválido; usando o lote padrão de 50.", 'warning')

    if filtro_data:
        try:
            datetime.strptime(filtro_data, '%Y-%m-%d')
        except ValueError:
            flash('Formato de data inválido. Use AAAA-MM-DD.', 'error')
            filtro_data = None

    offset = (pagina_atual - 1) * itens_por_pagina

    # Construir ORDER BY dinamicamente
    ordenar_sql_map = {
        'created_at_asc': 'H.timestamp ASC',
        'created_at_desc': 'H.timestamp DESC',
        'usuario_asc': 'U.nome ASC NULLS LAST',
        'usuario_desc': 'U.nome DESC NULLS LAST',
        'acao_asc': 'H.acao ASC',
        'acao_desc': 'H.acao DESC',
        'ip_asc': 'H.ip ASC',
        'ip_desc': 'H.ip DESC',
        'processo_asc': 'H.processo_id ASC NULLS LAST',
        'processo_desc': 'H.processo_id DESC NULLS LAST',
    }
    ordenar_sql = ordenar_sql_map.get(ordenar, 'H.timestamp DESC')

    # Query base para atividades
    base_query = """
        SELECT H.id, H.acao, H.contexto, H.processo_id, H.usuario_id, H.ip, H.timestamp, U.nome AS usuario_nome
        FROM logs H
        LEFT JOIN usuarios U ON H.usuario_id = U.id
        WHERE 1=1
    """
    count_query = "SELECT COUNT(*) AS count FROM logs H LEFT JOIN usuarios U ON H.usuario_id = U.id WHERE 1=1"

    where_clauses = []
    query_params = []
    
    if filtro_usuario_id:
        where_clauses.append("H.usuario_id = ?")
        query_params.append(filtro_usuario_id)

    if filtro_acao:
        where_clauses.append("H.acao = ?")
        query_params.append(filtro_acao)

    if filtro_data:
        # Usar strftime para converter o campo TEXT 'timestamp' para DATE para comparação
        where_clauses.append("strftime('%Y-%m-%d', H.timestamp) = ?")
        query_params.append(filtro_data)
    
    if where_clauses:
        base_query += " AND " + " AND ".join(where_clauses)
        count_query += " AND " + " AND ".join(where_clauses)

    try:
        total_registros_result = executar_query(count_query, query_params, fetch_one=True)
        total_registros = total_registros_result['count'] if total_registros_result else 0
        
        base_query += f" ORDER BY {ordenar_sql} LIMIT ? OFFSET ?"
        query_params_for_data = list(query_params)
        query_params_for_data.extend([itens_por_pagina, offset])
        
        atividades = executar_query(base_query, query_params_for_data)


        # Obter lista de usuários para filtro (apenas os que aparecem em logs)
        usuarios_com_log_raw = executar_query("SELECT DISTINCT U.id, U.nome, U.email FROM logs H JOIN usuarios U ON H.usuario_id = U.id WHERE U.ativo = 1 ORDER BY U.nome")
        usuarios_com_log = usuarios_com_log_raw
        
        # Obter lista de ações distintas para filtro
        acoes_distintas_raw = executar_query("SELECT DISTINCT acao FROM logs WHERE acao IS NOT NULL ORDER BY acao")
        acoes_list = [row['acao'] for row in acoes_distintas_raw]

        # Contagem para cards
        contagem_total_atividades = executar_query("SELECT COUNT(*) AS count FROM logs", fetch_one=True)['count']
        contagem_usuarios_ativos_em_log = executar_query("SELECT COUNT(DISTINCT usuario_id) AS count FROM logs WHERE usuario_id IS NOT NULL", fetch_one=True)['count']
        # Usar strftime('%Y-%m-%d', 'now', 'localtime') para obter a data atual no formato do banco
        contagem_hoje_atividades = executar_query("SELECT COUNT(*) AS count FROM logs WHERE strftime('%Y-%m-%d', timestamp) = strftime('%Y-%m-%d', 'now', 'localtime')", fetch_one=True)['count']
        
        total_paginas = (total_registros + itens_por_pagina - 1) // itens_por_pagina
        
        has_active_filters = any([
            filtro_usuario_id, filtro_acao, filtro_data,
            ordenar != 'created_at_desc'
        ])

    except Exception as e:
        logger.exception(f"Erro ao carregar histórico de atividades: {e}")
        flash('Erro ao carregar atividades. Por favor, tente novamente ou contate o suporte.', 'danger')
        # Redireciona para o dashboard em caso de erro grave no carregamento da página
        return redirect(url_for('auth.dashboard'))
    
    return render_template('atividades.html',
                           atividades=atividades,
                           total_registros=total_registros,
                           total_paginas=total_paginas,
                           pagina_atual=pagina_atual,
                           itens_por_pagina=itens_por_pagina,
                           filtro_usuario=filtro_usuario_id,
                           filtro_acao=filtro_acao,
                           filtro_data=filtro_data,
                           ordenar=ordenar,
                           usuarios=usuarios_com_log,
                           acoes=acoes_list,
                           contagem_total=contagem_total_atividades,
                           contagem_usuarios=contagem_usuarios_ativos_em_log,
                           contagem_hoje=contagem_hoje_atividades,
                           has_active_filters=has_active_filters
                           )


@atividades_bp.route('/auditoria', methods=['GET'])
@login_status_required
@permission_required('admin_logs')
def auditoria_seguranca():
    """Exibe a trilha administrativa e de segurança sem misturá-la à operação."""
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = min(100, max(1, request.args.get('itens_por_pagina', 50, type=int)))
    filtro_acao = proteger_input(request.args.get('acao'))
    filtro_ip = proteger_input(request.args.get('ip'))
    resultado = obter_logs_seguranca(
        {'acao': filtro_acao, 'ip': filtro_ip}, pagina=pagina, por_pagina=por_pagina
    )
    return render_template(
        'auditoria.html',
        eventos=resultado['logs'],
        total_registros=resultado['total'],
        total_paginas=resultado['total_paginas'],
        pagina_atual=resultado['pagina'],
        itens_por_pagina=resultado['por_pagina'],
        filtro_acao=filtro_acao or '',
        filtro_ip=filtro_ip or '',
    )