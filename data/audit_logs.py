"""Consultas de auditoria administrativa."""

import math

from data.database import executar_query
from utils.logger import logger

def obter_logs_auditoria(filtros=None, pagina=1, por_pagina=50):
    """
    Obtém logs de auditoria administrativa com filtros.
    
    Args:
        filtros: Dict com filtros (admin_id, acao, usuario_afetado_id, data_inicio, data_fim)
        pagina: Número da página
        por_pagina: Registros por página
    
    Returns:
        Dict com 'logs' e 'total'
    """
    try:
        query = "SELECT * FROM auditoria_admin WHERE 1=1"
        params = []
        
        if filtros:
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
        
        # Contar total
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = executar_query(count_query, params, fetch_one=True)
        total = total['COUNT(*)'] if total else 0
        
        # Adicionar paginação
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([por_pagina, (pagina - 1) * por_pagina])
        
        logs = executar_query(query, params)
        
        return {
            'logs': logs,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': math.ceil(total / por_pagina) if total > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter logs de auditoria: {e}", exc_info=True)
        return {'logs': [], 'total': 0, 'pagina': 1, 'por_pagina': por_pagina, 'total_paginas': 0}

