"""Consultas de auditoria administrativa e eventos de segurança."""

import math

from data.database import executar_query
from utils.logger import sistema_logger as logger


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
