"""Consultas de auditoria administrativa, eventos de segurança e atividades."""

import math

from data.database import executar_query
from utils.logger import sistema_logger as logger


# As três tabelas têm modelos históricos diferentes. A projeção normalizada
# permite que a interface consulte um único fluxo sem alterar os dados de origem.
_EVENTOS_UNION_SQL = """
    SELECT H.id,
           'atividade' AS fonte,
           H.acao,
           H.usuario_id,
           U.nome AS usuario_nome,
           H.processo_id AS alvo_id,
           H.ip,
           H.contexto AS detalhes,
           H.timestamp AS created_at,
           H.event_id,
           H.request_id,
           H.domain,
           H.event_type,
           H.severity
      FROM logs H
      LEFT JOIN usuarios U ON U.id = H.usuario_id
    UNION ALL
    SELECT A.id,
           'auditoria' AS fonte,
           A.acao,
           A.admin_id AS usuario_id,
           A.admin_nome AS usuario_nome,
           A.usuario_afetado_id AS alvo_id,
           A.ip,
           A.justificativa AS detalhes,
           A.created_at,
           A.event_id,
           A.request_id,
           'administrativo' AS domain,
           'admin.audit' AS event_type,
           'INFO' AS severity
      FROM auditoria_admin A
    UNION ALL
    SELECT S.id,
           'seguranca' AS fonte,
           S.tipo_tentativa AS acao,
           S.usuario_id,
           S.usuario_nome,
           S.alvo_user_id AS alvo_id,
           S.ip,
           S.detalhes,
           S.created_at,
           S.event_id,
           S.request_id,
           'seguranca' AS domain,
           'security.denied' AS event_type,
           CASE WHEN S.bloqueado = 1 THEN 'WARNING' ELSE 'INFO' END AS severity
      FROM tentativas_acesso_nao_autorizado S
"""

_EVENTOS_ORDER_MAP = {
    'created_at_asc': 'created_at ASC, id ASC',
    'created_at_desc': 'created_at DESC, id DESC',
    'usuario_asc': 'LOWER(COALESCE(usuario_nome, \'\')) ASC, created_at DESC, id DESC',
    'usuario_desc': 'LOWER(COALESCE(usuario_nome, \'\')) DESC, created_at DESC, id DESC',
    'fonte_asc': 'fonte ASC, created_at DESC, id DESC',
    'fonte_desc': 'fonte DESC, created_at DESC, id DESC',
    'acao_asc': 'LOWER(COALESCE(acao, \'\')) ASC, created_at DESC, id DESC',
    'acao_desc': 'LOWER(COALESCE(acao, \'\')) DESC, created_at DESC, id DESC',
    'ip_asc': 'COALESCE(ip, \'\') ASC, created_at DESC, id DESC',
    'ip_desc': 'COALESCE(ip, \'\') DESC, created_at DESC, id DESC',
}


def _normalizar_filtros_eventos(filtros):
    filtros = filtros or {}
    fonte = str(filtros.get('fonte') or 'todos').strip().lower()
    if fonte not in {'todos', 'atividade', 'auditoria', 'seguranca'}:
        fonte = 'todos'

    ordenar = str(filtros.get('ordenar') or 'created_at_desc').strip()
    if ordenar not in _EVENTOS_ORDER_MAP:
        ordenar = 'created_at_desc'

    return {
        'fonte': fonte,
        'busca': str(filtros.get('busca') or '').strip(),
        'usuario_id': filtros.get('usuario_id'),
        'data': str(filtros.get('data') or '').strip(),
        'ordenar': ordenar,
    }


def obter_eventos_unificados(filtros=None, pagina=1, por_pagina=50):
    """Retorna atividades, auditoria e segurança em uma lista paginada.

    A função apenas lê as tabelas existentes e mantém os contratos legados de
    ``obter_logs_auditoria`` e ``obter_logs_seguranca`` intactos.
    """
    filtros = _normalizar_filtros_eventos(filtros)
    pagina = max(1, int(pagina or 1))
    por_pagina = min(100, max(1, int(por_pagina or 50)))

    clauses = []
    params = []
    if filtros['fonte'] != 'todos':
        clauses.append('fonte = ?')
        params.append(filtros['fonte'])

    if filtros['usuario_id']:
        clauses.append('usuario_id = ?')
        params.append(filtros['usuario_id'])

    if filtros['data']:
        clauses.append("strftime('%Y-%m-%d', created_at) = ?")
        params.append(filtros['data'])

    if filtros['busca']:
        search = f"%{filtros['busca']}%"
        clauses.append("""(
            acao LIKE ? OR usuario_nome LIKE ? OR ip LIKE ? OR detalhes LIKE ?
            OR CAST(alvo_id AS TEXT) LIKE ? OR event_id LIKE ? OR request_id LIKE ?
        )""")
        params.extend([search] * 7)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ''
    union_query = f"SELECT * FROM ({_EVENTOS_UNION_SQL}) eventos{where}"
    order_by = _EVENTOS_ORDER_MAP[filtros['ordenar']]

    try:
        total_row = executar_query(
            f"SELECT COUNT(*) AS total FROM ({_EVENTOS_UNION_SQL}) eventos{where}",
            params,
            fetch_one=True,
        )
        total = total_row['total'] if total_row else 0
        eventos = executar_query(
            f"{union_query} ORDER BY {order_by} LIMIT ? OFFSET ?",
            params + [por_pagina, (pagina - 1) * por_pagina],
        )
        return {
            'logs': eventos,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': math.ceil(total / por_pagina) if total else 0,
            'filtros': filtros,
        }
    except Exception as exc:
        logger.error(f'Erro ao obter fluxo unificado de eventos: {exc}', exc_info=True)
        return {
            'logs': [],
            'total': 0,
            'pagina': 1,
            'por_pagina': por_pagina,
            'total_paginas': 0,
            'filtros': filtros,
        }


def obter_eventos_filtros():
    """Obtém opções compactas para os filtros da tela unificada."""
    try:
        usuarios = executar_query(
            """
            SELECT DISTINCT U.id, U.nome
              FROM usuarios U
              JOIN (
                    SELECT usuario_id FROM logs WHERE usuario_id IS NOT NULL
                    UNION
                    SELECT admin_id FROM auditoria_admin WHERE admin_id IS NOT NULL
                    UNION
                    SELECT usuario_id FROM tentativas_acesso_nao_autorizado WHERE usuario_id IS NOT NULL
              ) E ON E.usuario_id = U.id
             WHERE U.ativo = 1
             ORDER BY U.nome
            """
        )
        acoes = executar_query(
            f"SELECT DISTINCT acao FROM ({_EVENTOS_UNION_SQL}) eventos WHERE acao IS NOT NULL ORDER BY acao"
        )
        return {'usuarios': usuarios, 'acoes': [row['acao'] for row in acoes]}
    except Exception as exc:
        logger.error(f'Erro ao obter filtros do fluxo unificado: {exc}', exc_info=True)
        return {'usuarios': [], 'acoes': []}


def obter_logs_auditoria(filtros=None, pagina=1, por_pagina=50):
    """Consulta a auditoria administrativa preservando a API existente."""
    try:
        filtros = filtros or {}
        pagina = max(1, int(pagina or 1))
        por_pagina = min(100, max(1, int(por_pagina or 50)))
        query = "SELECT * FROM auditoria_admin WHERE 1=1"
        params = []
        if filtros.get('admin_id'):
            query += " AND admin_id = ?"
            params.append(filtros['admin_id'])
        if filtros.get('acao'):
            query += " AND acao = ?"
            params.append(filtros['acao'])
        if filtros.get('usuario_afetado_id'):
            query += " AND usuario_afetado_id = ?"
            params.append(filtros['usuario_afetado_id'])
        if filtros.get('data_inicio'):
            query += " AND created_at >= ?"
            params.append(filtros['data_inicio'])
        if filtros.get('data_fim'):
            query += " AND created_at <= ?"
            params.append(filtros['data_fim'])

        total_row = executar_query(query.replace('SELECT *', 'SELECT COUNT(*)'), params, fetch_one=True)
        total = total_row['COUNT(*)'] if total_row else 0
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        logs = executar_query(query, params + [por_pagina, (pagina - 1) * por_pagina])
        return {
            'logs': logs, 'total': total, 'pagina': pagina, 'por_pagina': por_pagina,
            'total_paginas': math.ceil(total / por_pagina) if total else 0,
        }
    except Exception as exc:
        logger.error(f'Erro ao obter logs de auditoria: {exc}', exc_info=True)
        return {'logs': [], 'total': 0, 'pagina': 1, 'por_pagina': por_pagina, 'total_paginas': 0}


def obter_logs_seguranca(filtros=None, pagina=1, por_pagina=50):
    """Une auditoria administrativa e tentativas bloqueadas para investigação."""
    filtros = filtros or {}
    pagina = max(1, int(pagina or 1))
    por_pagina = min(100, max(1, int(por_pagina or 50)))
    params = []
    clauses = []
    if filtros.get('acao'):
        clauses.append('acao LIKE ?')
        params.append(f"%{filtros['acao']}%")
    if filtros.get('ip'):
        clauses.append('ip = ?')
        params.append(filtros['ip'])
    where = (' WHERE ' + ' AND '.join(clauses)) if clauses else ''
    try:
        count_sql = f"""
            SELECT COUNT(*) AS total FROM (
                SELECT acao, ip FROM auditoria_admin
                UNION ALL
                SELECT tipo_tentativa AS acao, ip FROM tentativas_acesso_nao_autorizado
            ) eventos {where}
        """
        total_row = executar_query(count_sql, params, fetch_one=True)
        total = total_row['total'] if total_row else 0
        data_sql = f"""
            SELECT * FROM (
                SELECT id, 'auditoria_admin' AS fonte, acao, admin_id AS usuario_id,
                       admin_nome AS usuario_nome, usuario_afetado_id AS alvo_id,
                       ip, user_agent, justificativa AS detalhes, created_at,
                       event_id, request_id
                  FROM auditoria_admin
                UNION ALL
                SELECT id, 'seguranca' AS fonte, tipo_tentativa AS acao, usuario_id,
                       usuario_nome, alvo_user_id AS alvo_id, ip, user_agent,
                       detalhes, created_at, event_id, request_id
                  FROM tentativas_acesso_nao_autorizado
            ) eventos {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        eventos = executar_query(data_sql, params + [por_pagina, (pagina - 1) * por_pagina])
        return {
            'logs': eventos, 'total': total, 'pagina': pagina, 'por_pagina': por_pagina,
            'total_paginas': math.ceil(total / por_pagina) if total else 0,
        }
    except Exception as exc:
        logger.error(f'Erro ao obter logs de segurança: {exc}', exc_info=True)
        return {'logs': [], 'total': 0, 'pagina': 1, 'por_pagina': por_pagina, 'total_paginas': 0}
