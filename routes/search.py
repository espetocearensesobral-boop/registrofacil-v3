# registrofacil/routes/search.py

from flask import Blueprint, request, jsonify, session, url_for
from routes.auth import is_logged_in_status, login_status_required, get_client_ip, proteger_input, verificar_csrf_token

from models import (
    executar_query,
    gravar_log,
    listar_processos,
    obter_status_processo_config,
    LOCK_TIMEOUT_MINUTES
)
from utils.logger import logger
from utils.helpers import formatar_data, get_contrast_color

search_bp = Blueprint('search', __name__, url_prefix='/api')

@search_bp.route('/global_search', methods=['GET'])
@login_status_required
def global_search():
    query = proteger_input(request.args.get('q', ''))
    usuario_id = session.get('usuario_id')
    ip = get_client_ip()

    if not query:
        return jsonify([])

    results = []
    is_numeric_query = query.isdigit()
    numeric_query_int = int(query) if is_numeric_query else -1
    
    max_results = 10

    # Lógica para excluir status finalizados da busca
    status_excluir_names = ['Concluído', 'Arquivado', 'Finalizado']
    all_status = obter_status_processo_config()
    status_excluir_ids = [s['id'] for s in all_status if s['nome'] in status_excluir_names]

    base_sql = """
        SELECT p.id, p.titular, p.matricula, p.numero_processo, p.apresentante,
               p.data_entrada, p.prazo_final,
               p.data_conclusao, sp.nome as status_nome, sp.hex_color
        FROM processos p
        LEFT JOIN status_processo sp ON p.status_id = sp.id
    """
    where_clauses = []
    query_params = []

    # --- LÓGICA DE BUSCA GLOBAL EXPANDIDA ---
    query_param_like = f'%{query}%'
    if is_numeric_query:
        # Se a busca é um número, procura pelo ID, número do processo ou matrícula
        where_clauses.append("(p.id = ? OR p.numero_processo LIKE ? OR p.matricula LIKE ?)")
        query_params.extend([numeric_query_int, query_param_like, query_param_like])
    else:
        # Se a busca é texto, procura em titular, matrícula, número do processo e apresentante
        where_clauses.append(
            "(p.titular LIKE ? OR p.matricula LIKE ? OR p.numero_processo LIKE ? OR p.apresentante LIKE ?)"
        )
        query_params.extend([query_param_like, query_param_like, query_param_like, query_param_like])
    
    # Adiciona o filtro para não mostrar processos finalizados
    if status_excluir_ids:
        status_excluir_placeholders = ','.join(['?' for _ in status_excluir_ids])
        where_clauses.append(f"sp.id NOT IN ({status_excluir_placeholders})")
        query_params.extend(status_excluir_ids)

    # Monta a query final
    final_sql = f"{base_sql} WHERE {' AND '.join(where_clauses)} ORDER BY p.id DESC LIMIT ?"
    query_params.append(max_results)

    try:
        processos = executar_query(final_sql, query_params)
        for p in processos:
            results.append({
                'id': p['id'],
                'title': p['titular'],
                'matricula': p.get('matricula', 'N/A'),
                'type': 'Processo',
                'url': url_for('processos.visualizar', processo_id=p['id']),
                'data_entrada': p.get('data_entrada', ''),
                'data_conclusao': p.get('data_conclusao', ''),
                'status_nome': p.get('status_nome', ''),
                'hex_color': p.get('hex_color', ''),
                'numero_processo': p.get('numero_processo', ''),
                'apresentante': p.get('apresentante', ''),
            })
    except Exception as e:
        logger.error(f"Erro na pesquisa de processos: {e}", exc_info=True)
        return jsonify(success=False, message='Falha ao pesquisar processos.', type='danger'), 500

    gravar_log('pesquisa_realizada', None, usuario_id, ip, f"Pesquisa global por: '{query}' - {len(results)} resultados.")
    logger.info(f"Pesquisa global por '{query}' realizada por {usuario_id}. Resultados: {len(results)}")

    return jsonify(results)


@search_bp.route('/smart_search', methods=['GET'])
@login_status_required
def smart_search():
    """Busca completa de processos para o modal Buscar."""
    query = proteger_input(request.args.get('q', '').strip())
    pagina = max(request.args.get('pagina', 1, type=int), 1)
    por_pagina = min(max(request.args.get('por_pagina', 25, type=int), 10), 100)
    filtros = {'busca': query}
    try:
        resultado = listar_processos(filtros, pagina, por_pagina, 'id_desc')
        processos = []
        for processo in resultado['processos'] or []:
            item = dict(processo)
            item['visualizar_url'] = url_for('processos.visualizar', processo_id=item['id'])
            item['imprimir_url'] = url_for('processos.gerar_relatorio_customizado', processo_id=item['id'], tipo='html_print')
            item['baixar_url'] = url_for('processos.gerar_pdf', processo_id=item['id'])
            processos.append(item)
        gravar_log('pesquisa_inteligente_realizada', None, session.get('usuario_id'), get_client_ip(), f"Busca: '{query}' - {resultado['total_records']} resultados.")
        return jsonify(success=True, processos=processos, total=resultado['total_records'], pagina=pagina, total_paginas=resultado['total_pages'])
    except Exception as exc:
        logger.error(f"Erro na busca inteligente: {exc}", exc_info=True)
        return jsonify(success=False, message='Falha ao pesquisar processos.'), 500


# ... (o restante do arquivo search.py permanece o mesmo) ...

@search_bp.route('/acquire_lock', methods=['POST'])
@login_status_required
def api_acquire_lock():
    if not verificar_csrf_token(request.json.get('csrf_token')):
        logger.error(f"Token CSRF inválido em api_acquire_lock. IP: {get_client_ip()}")
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403

    table_name = request.json.get('table_name')
    record_id_raw = request.json.get('record_id')
    ip = get_client_ip()

    try:
        record_id = int(record_id_raw)
        if record_id <= 0:
            raise ValueError("ID do registro deve ser um número inteiro positivo.")
    except (ValueError, TypeError):
        return jsonify(success=False, message="ID do registro inválido (deve ser um número inteiro positivo).", type='danger'), 400

    user_id = session.get('usuario_id')

    if not all([table_name, user_id]):
        return jsonify(success=False, message="Dados incompletos para adquirir bloqueio.", type='warning'), 400
    
    from models import acquire_lock 

    result = acquire_lock(table_name, record_id, user_id, LOCK_TIMEOUT_MINUTES)
    if result is True:
        gravar_log('acquire_lock', record_id, user_id, ip, f"Bloqueio adquirido para {table_name}:{record_id}")
        return jsonify(success=True, message="Bloqueio adquirido com sucesso!"), 200
    else:
        status_code = result.get('code', 500)
        gravar_log('acquire_lock_falha', record_id, user_id, ip, f"Falha ao adquirir bloqueio para {table_name}:{record_id}. Motivo: {result.get('error')}")
        return jsonify(success=False, message=result.get('error', 'Falha desconhecida ao adquirir bloqueio.'), type=result.get('type', 'danger')), status_code

@search_bp.route('/renew_lock', methods=['POST'])
@login_status_required
def api_renew_lock():
    if not verificar_csrf_token(request.json.get('csrf_token')):
        logger.error(f"Token CSRF inválido em api_renew_lock. IP: {get_client_ip()}")
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403

    table_name = request.json.get('table_name')
    record_id_raw = request.json.get('record_id')
    ip = get_client_ip()
    
    try:
        record_id = int(record_id_raw)
        if record_id <= 0:
            raise ValueError("ID do registro deve ser um número inteiro positivo.")
    except (ValueError, TypeError):
        return jsonify(success=False, message="ID do registro inválido (deve ser um número inteiro positivo).", type='danger'), 400

    user_id = session.get('usuario_id')

    if not all([table_name, user_id]):
        return jsonify(success=False, message="Dados incompletos para renovar bloqueio.", type='warning'), 400

    from models import renew_lock
    result = renew_lock(table_name, record_id, user_id, LOCK_TIMEOUT_MINUTES)
    if result.get('success'):
        gravar_log('renew_lock', record_id, user_id, ip, f"Bloqueio renovado para {table_name}:{record_id}")
        return jsonify(success=True, message="Bloqueio renovado com sucesso!"), 200
    else:
        status_code = result.get('code', 500)
        gravar_log('renew_lock_falha', record_id, user_id, ip, f"Falha ao renovar bloqueio para {table_name}:{record_id}. Motivo: {result.get('message')}")
        return jsonify(success=False, message=result.get('message', 'Falha desconhecida ao renovar bloqueio.'), type=result.get('type', 'danger')), status_code

@search_bp.route('/release_lock', methods=['POST'])
@login_status_required
def api_release_lock():
    if request.is_json:
        data = request.json
    else:
        data = request.form
    ip = get_client_ip()

    if not verificar_csrf_token(data.get('csrf_token')):
        logger.error(f"Token CSRF inválido em api_release_lock. IP: {get_client_ip()}")
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403

    table_name = data.get('table_name')
    record_id_raw = data.get('record_id')
    
    try:
        record_id = int(record_id_raw)
        if record_id <= 0:
            raise ValueError("ID do registro deve ser um número inteiro positivo.")
    except (ValueError, TypeError):
        return jsonify(success=False, message="ID do registro inválido (deve ser um número inteiro positivo).", type='danger'), 400

    user_id = session.get('usuario_id')

    if not all([table_name, record_id]):
        return jsonify(success=False, message="Dados incompletos para liberar bloqueio.", type='warning'), 400

    from models import release_lock
    result = release_lock(table_name, record_id, user_id)
    if result.get('success'):
        gravar_log('release_lock', record_id, user_id, ip, f"Bloqueio liberado para {table_name}:{record_id}")
        return jsonify(success=True, message="Bloqueio liberado com sucesso!"), 200
    else:
        status_code = result.get('code', 500)
        gravar_log('release_lock_falha', record_id, user_id, ip, f"Falha ao liberar bloqueio para {table_name}:{record_id}. Motivo: {result.get('message')}")
        return jsonify(success=False, message=result.get('message', 'Falha desconhecida ao liberar bloqueio.'), type=result.get('type', 'danger')), status_code