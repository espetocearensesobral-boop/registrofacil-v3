"""Busca global em processos e cadastros."""

from data.database import executar_query
from utils.logger import logger

def busca_full_text(termo, usuario_id=None, limit=50):
    """
    Busca usando FTS5 para resultados rápidos e relevantes.
    
    Args:
        termo: Termo de busca
        usuario_id: ID do usuário (para filtros de permissão no futuro)
        limit: Número máximo de resultados
    
    Returns:
        Lista de processos encontrados
    """
    try:
        # Preparar termo para FTS5 (adiciona wildcards para busca parcial)
        termo_fts = f'"{termo}"*' if termo else '*'
        
        query = """
            SELECT 
                p.*,
                t.nome as tipo_nome,
                s.nome as status_nome,
                s.hex_color as status_cor,
                u.nome as responsavel_nome,
                bm25(processos_fts) as relevancia
            FROM processos_fts fts
            JOIN processos p ON fts.id = p.id
            LEFT JOIN tipos_servico t ON p.tipo_id = t.id
            LEFT JOIN status_processo s ON p.status_id = s.id
            LEFT JOIN usuarios u ON p.responsavel_id = u.id
            WHERE processos_fts MATCH ?
            ORDER BY relevancia
            LIMIT ?
        """
        
        resultados = executar_query(query, [termo_fts, limit], fetch_all=True)
        return resultados or []
    except Exception as e:
        logger.warning(f"Busca FTS5 falhou, usando busca tradicional: {e}")
        # Fallback para busca tradicional se FTS falhar
        return busca_tradicional(termo, limit)

def busca_tradicional(termo, limit=50):
    """Busca tradicional com LIKE (fallback quando FTS não disponível)."""
    query = """
        SELECT 
            p.*,
            t.nome as tipo_nome,
            s.nome as status_nome,
            s.hex_color as status_cor,
            u.nome as responsavel_nome
        FROM processos p
        LEFT JOIN tipos_servico t ON p.tipo_id = t.id
        LEFT JOIN status_processo s ON p.status_id = s.id
        LEFT JOIN usuarios u ON p.responsavel_id = u.id
        WHERE 
            p.numero_processo LIKE ? OR
            p.titular LIKE ? OR
            p.matricula LIKE ? OR
            p.apresentante LIKE ? OR
            p.observacoes LIKE ?
        ORDER BY p.created_at DESC
        LIMIT ?
    """
    termo_like = f"%{termo}%"
    return executar_query(query, [termo_like] * 5 + [limit], fetch_all=True) or []

