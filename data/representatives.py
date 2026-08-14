"""Consultas e operações de representantes."""

from data.database import executar_query


def listar_representantes(filtros=None, pagina=1, registros_por_pagina=10):
    """Lista representantes com filtros, ordenação e paginação."""
    filtros = filtros or {}
    pagina = max(int(pagina or 1), 1)
    registros_por_pagina = max(int(registros_por_pagina or 10), 1)

    where = []
    params = []
    busca = (filtros.get("busca") or "").strip()
    if busca:
        like = f"%{busca}%"
        where.append("(r.nome LIKE ? OR r.telefone LIKE ? OR r.email LIKE ?)")
        params.extend([like, like, like])

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    order_map = {
        "nome": "r.nome COLLATE NOCASE",
        "telefone": "r.telefone COLLATE NOCASE",
        "email": "r.email COLLATE NOCASE",
        "created_at": "r.created_at",
        "total_processos": "total_processos",
    }
    order_by = order_map.get(filtros.get("ordenar"), "r.nome COLLATE NOCASE")
    direction = "DESC" if str(filtros.get("direcao", "asc")).lower() == "desc" else "ASC"

    count_row = executar_query(
        f"SELECT COUNT(*) AS total FROM representantes r {where_sql}",
        params,
        fetch_one=True,
    )
    total_records = int(count_row["total"] if count_row else 0)
    total_pages = (total_records + registros_por_pagina - 1) // registros_por_pagina
    offset = (pagina - 1) * registros_por_pagina
    rows = executar_query(
        f"""
        SELECT r.id, r.nome, r.telefone, r.email, r.created_at, r.updated_at,
               COUNT(p.id) AS total_processos,
               MAX(p.id) AS ultimo_registro_id,
               (SELECT p2.matricula FROM processos p2
                  WHERE p2.representante = r.nome
                  ORDER BY p2.id DESC LIMIT 1) AS ultimo_registro_matricula
          FROM representantes r
          LEFT JOIN processos p ON p.representante = r.nome
         {where_sql}
         GROUP BY r.id, r.nome, r.telefone, r.email, r.created_at, r.updated_at
         ORDER BY {order_by} {direction}
         LIMIT ? OFFSET ?
        """,
        params + [registros_por_pagina, offset],
        fetch_all=True,
    )
    return {
        "representantes": rows or [],
        "total_records": total_records,
        "total_pages": total_pages,
        "pagina_atual": pagina,
        "registros_por_pagina": registros_por_pagina,
    }


def get_representante_by_id(representante_id):
    return executar_query(
        """
        SELECT r.id, r.nome, r.telefone, r.email, r.created_at, r.updated_at,
               COUNT(p.id) AS total_processos,
               MAX(p.id) AS ultimo_registro_id,
               (SELECT p2.matricula FROM processos p2
                  WHERE p2.representante = r.nome
                  ORDER BY p2.id DESC LIMIT 1) AS ultimo_registro_matricula
          FROM representantes r
          LEFT JOIN processos p ON p.representante = r.nome
         WHERE r.id = ?
         GROUP BY r.id, r.nome, r.telefone, r.email, r.created_at, r.updated_at
        """,
        [representante_id],
        fetch_one=True,
    )


def get_historico_servicos_representante(nome):
    return executar_query(
        """
        SELECT p.id, p.matricula, p.data_entrada, p.prazo_final,
               t.nome AS tipo_servico_nome,
               s.nome AS status_nome,
               s.hex_color
          FROM processos p
          LEFT JOIN tipos_servico t ON t.id = p.tipo_id
          LEFT JOIN status_processo s ON s.id = p.status_id
         WHERE p.representante = ?
         ORDER BY p.data_entrada DESC, p.id DESC
        """,
        [nome],
        fetch_all=True,
    ) or []


def buscar_representantes_json(termo):
    termo = (termo or "").strip()
    like = f"%{termo}%"
    return executar_query(
        """
        SELECT id, nome, telefone, email
          FROM representantes
         WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
         ORDER BY nome COLLATE NOCASE ASC
         LIMIT 20
        """,
        [like, like, like],
        fetch_all=True,
    ) or []


def representante_tem_processos(representante_id):
    row = get_representante_by_id(representante_id)
    if not row:
        return False
    count = executar_query(
        "SELECT COUNT(*) AS total FROM processos WHERE representante = ?",
        [row["nome"]],
        fetch_one=True,
    )
    return bool(count and count["total"] > 0)


def editar_representante(representante_id, nome, telefone=None, email=None):
    return executar_query(
        """
        UPDATE representantes
           SET nome = ?, telefone = ?, email = ?,
               updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
         WHERE id = ?
        """,
        [nome, telefone, email, representante_id],
    )


def excluir_representante(representante_id):
    return executar_query(
        "DELETE FROM representantes WHERE id = ?",
        [representante_id],
    )
