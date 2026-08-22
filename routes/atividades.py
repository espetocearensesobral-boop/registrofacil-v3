# registrofacil/routes/atividades.py
"""Compatibilidade de URLs legadas para o histórico unificado em Configurações."""

from flask import Blueprint, redirect, request, url_for

from routes.auth import login_status_required, proteger_input
from routes.permissoes import permission_required

atividades_bp = Blueprint('atividades', __name__, url_prefix='/atividades')


def _redirect_to_unified_events(**params):
    query = {'tab': 'atividades'}
    query.update({key: value for key, value in params.items() if value not in (None, '')})
    return redirect(url_for('configuracoes.index', **query))


@atividades_bp.route('/historico', methods=['GET'])
@login_status_required
@permission_required('atividades_visualizar')
def historico():
    """Mantém favoritos antigos apontando para o histórico consolidado."""
    return _redirect_to_unified_events(
        eventos_fonte='atividade',
        eventos_busca=proteger_input(request.args.get('acao')),
        eventos_usuario=request.args.get('usuario', type=int),
        eventos_data=proteger_input(request.args.get('data')),
        eventos_ordenar=proteger_input(request.args.get('ordenar')) or 'created_at_desc',
        pagina=request.args.get('pagina', type=int),
        eventos_itens_por_pagina=request.args.get('itens_por_pagina', type=int),
    )


@atividades_bp.route('/auditoria', methods=['GET'])
@login_status_required
@permission_required('admin_logs')
def auditoria_seguranca():
    """Mantém o endpoint legado, agora direcionado ao fluxo unificado."""
    busca = proteger_input(request.args.get('acao')) or proteger_input(request.args.get('ip'))
    return _redirect_to_unified_events(
        eventos_busca=busca,
        pagina=request.args.get('pagina', type=int),
        eventos_itens_por_pagina=request.args.get('itens_por_pagina', type=int),
    )
