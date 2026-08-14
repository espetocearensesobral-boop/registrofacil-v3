"""Consultas administrativas e seleção de usuários."""

from data.database import executar_query

def obter_usuarios_para_selecao():
    return executar_query("SELECT id, nome FROM usuarios WHERE ativo = 1 ORDER BY nome ASC")

def get_users_for_admin_list(filters, page, per_page, order_by):
    base_query = """
        SELECT id, usuario, nome, email, created_at, ativo, deleted_at, role
        FROM usuarios U
    """
    count_query = "SELECT COUNT(*) AS total_count FROM usuarios U"

    where_clauses = []
    query_params = []

    if filters.get('status') == 'ativo':
        where_clauses.append("U.ativo = 1")
    elif filters.get('status') == 'inativo':
        where_clauses.append("U.ativo = 0")

    if filters.get('busca'):
        search_term = f"%{filters['busca']}%"
        where_clauses.append("(U.usuario LIKE ? OR U.nome LIKE ? OR U.email LIKE ?)")
        query_params.extend([search_term, search_term, search_term])

    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
        count_query += " WHERE " + " AND ".join(where_clauses)

    order_map = {
        'id_asc': 'U.id ASC',
        'id_desc': 'U.id DESC',
        'usuario_asc': 'U.usuario COLLATE NOCASE ASC',
        'usuario_desc': 'U.usuario COLLATE NOCASE DESC',
        'nome_asc': 'U.nome COLLATE NOCASE ASC',
        'nome_desc': 'U.nome COLLATE NOCASE DESC',
        'email_asc': 'U.email COLLATE NOCASE ASC',
        'email_desc': 'U.email COLLATE NOCASE DESC',
        'created_at_asc': 'U.created_at ASC',
        'created_at_desc': 'U.created_at DESC',
        'status_asc': 'U.ativo ASC, U.created_at DESC',
        'status_desc': 'U.ativo DESC, U.created_at DESC',
    }
    order_clause = order_map.get(order_by, 'U.ativo DESC, U.created_at DESC')
    base_query += f" ORDER BY {order_clause}"

    offset = (page - 1) * per_page

    base_query = f"{base_query} LIMIT ? OFFSET ?"
    query_params_for_data = list(query_params)
    query_params_for_data.extend([per_page, offset])

    total_records_result = executar_query(count_query, query_params, fetch_one=True)
    total_records = total_records_result['total_count'] if total_records_result and 'total_count' in total_records_result else 0
    total_pages = (total_records + per_page - 1) // per_page
    if total_pages == 0 and total_records > 0:
        total_pages = 1

    users = executar_query(base_query, query_params_for_data)

    return {
        'users': users,
        'total_records': total_records,
        'total_pages': total_pages
    }

