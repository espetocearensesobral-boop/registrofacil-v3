"""Serviços de titulares, apresentantes e sincronização com processos."""

import math
from datetime import datetime

from data.database import executar_query, get_sqlite_connection
from data.processes import registrar_historico_processo

def listar_titulares(filtros=None, pagina=1, registros_por_pagina=10):
    """Lista titulares com paginação e filtros."""
    import math
    offset = (pagina - 1) * registros_por_pagina
    
    query = """SELECT t.*,
               CASE WHEN p.id IS NULL THEN NULL
                    WHEN (p.possui_matricula = 1 OR (p.possui_matricula IS NULL AND p.matricula IS NOT NULL)) AND p.matricula IS NOT NULL THEN p.matricula
                    ELSE 'Sem Matrícula'
               END as ultimo_registro_matricula,
               (SELECT COUNT(*) FROM processos pr
                  WHERE pr.titular_id = t.id
                     OR (pr.titular_id IS NULL AND pr.titular = t.nome)) as total_processos
               FROM titulares t LEFT JOIN processos p ON t.ultimo_registro_id = p.id WHERE 1=1"""
    params = []
    
    if filtros:
        if filtros.get('busca'):
            query += " AND (t.nome LIKE ? OR t.email LIKE ? OR t.telefone LIKE ?)"
            busca = f"%{filtros['busca']}%"
            params.extend([busca, busca, busca])
            
    # Obter total de registros para paginação
    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_records = executar_query(count_query, params, fetch_one=True)['COUNT(*)']
    
    # Ordenação dinâmica
    ordenar = filtros.get('ordenar', 'nome') if filtros else 'nome'
    direcao = filtros.get('direcao', 'asc') if filtros else 'asc'
    
    colunas_validas = {'id': 't.id', 'nome': 't.nome', 'email': 't.email', 'telefone': 't.telefone', 'processos': 'total_processos'}
    col_sql = colunas_validas.get(ordenar, 't.nome')
    dir_sql = 'DESC' if direcao == 'desc' else 'ASC'
    
    query += f" ORDER BY {col_sql} {dir_sql} LIMIT ? OFFSET ?"
    params.extend([registros_por_pagina, offset])
    
    titulares = executar_query(query, params, fetch_all=True)
    
    return {
        'titulares': titulares,
        'total_records': total_records,
        'total_pages': math.ceil(total_records / registros_por_pagina) if total_records > 0 else 0
    }

def get_titular_by_id(titular_id):
    """Obtém detalhes de um titular pelo ID."""
    query = """SELECT t.*,
               CASE WHEN p.id IS NULL THEN NULL
                    WHEN (p.possui_matricula = 1 OR (p.possui_matricula IS NULL AND p.matricula IS NOT NULL)) AND p.matricula IS NOT NULL THEN p.matricula
                    ELSE 'Sem Matrícula'
               END as ultimo_registro_matricula
               FROM titulares t LEFT JOIN processos p ON t.ultimo_registro_id = p.id WHERE t.id = ?"""
    return executar_query(query, [titular_id], fetch_one=True)

def titular_tem_processos(titular_id):
    """Verifica vínculo por ID e mantém fallback para processos legados."""
    tit = executar_query("SELECT nome FROM titulares WHERE id = ?", [titular_id], fetch_one=True)
    if not tit:
        return False
    result = executar_query(
        """
        SELECT COUNT(*) AS cnt
          FROM processos
         WHERE titular_id = ?
            OR (titular_id IS NULL AND titular = ?)
        """,
        [titular_id, tit['nome']],
        fetch_one=True,
    )
    return result['cnt'] > 0 if result else False

def _sincronizar_processos_cadastro(
    cadastro_id,
    nome_anterior,
    nome_novo,
    telefone_novo,
    email_novo,
    tipo_cadastro,
    usuario_id=None,
    processo_excluido_id=None,
    connection=None,
):
    """Propaga dados de um cadastro para processos e audita as mudanças."""
    if not cadastro_id:
        return []
    if tipo_cadastro not in {'titular', 'apresentante'}:
        raise ValueError("Tipo de cadastro inválido para sincronização.")

    nome_coluna = tipo_cadastro
    id_coluna = f"{tipo_cadastro}_id"
    telefone_coluna = f"{tipo_cadastro}_telefone"
    email_coluna = f"{tipo_cadastro}_email"

    where_sql = f"{id_coluna} = ?"
    params = [cadastro_id]
    if nome_anterior:
        where_sql += f" OR ({id_coluna} IS NULL AND {nome_coluna} = ?)"
        params.append(nome_anterior)

    processos = executar_query(
        f"""
        SELECT id, {nome_coluna} AS nome_atual,
               {telefone_coluna} AS telefone_atual,
               {email_coluna} AS email_atual
          FROM processos
         WHERE {where_sql}
        """,
        params,
        fetch_all=True,
        connection=connection,
    ) or []

    alteracoes = []
    prefixo = 'titular' if tipo_cadastro == 'titular' else 'apresentante'
    nomes_exibicao = {
        'nome': 'Titular' if tipo_cadastro == 'titular' else 'Apresentante',
        'telefone': f"Telefone do {prefixo}",
        'email': f"E-mail do {prefixo}",
    }

    for processo in processos:
        if processo_excluido_id is not None and int(processo['id']) == int(processo_excluido_id):
            continue

        nome_antigo_processo = processo['nome_atual'] or ''
        telefone_antigo_processo = processo['telefone_atual'] or ''
        email_antigo_processo = processo['email_atual'] or ''
        valores = [nome_novo, cadastro_id, telefone_novo, email_novo]

        executar_query(
            f"""
            UPDATE processos
               SET {nome_coluna} = ?, {id_coluna} = ?,
                   {telefone_coluna} = ?, {email_coluna} = ?,
                   updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
             WHERE id = ?
            """,
            valores + [processo['id']],
            connection=connection,
        )

        comparacoes = [
            ('nome', nome_antigo_processo, nome_novo or ''),
            ('telefone', telefone_antigo_processo, telefone_novo or ''),
            ('email', email_antigo_processo, email_novo or ''),
        ]
        for campo, valor_antigo, valor_novo in comparacoes:
            if str(valor_antigo).strip() == str(valor_novo).strip():
                continue
            registrar_historico_processo(
                processo_id=processo['id'],
                usuario_id=usuario_id,
                campo_alterado=nomes_exibicao[campo],
                valor_antigo=str(valor_antigo),
                valor_novo=str(valor_novo),
                observacao_adicional=(
                    f"Alteração sincronizada a partir do cadastro "
                    f"{tipo_cadastro} ID {cadastro_id}."
                ),
                connection=connection,
            )
            alteracoes.append(processo['id'])

    return sorted(set(alteracoes))

def editar_titular(titular_id, nome, telefone, email, connection=None, usuario_id=None):
    """Atualiza um titular e sincroniza os processos que armazenam seu nome."""
    from datetime import datetime

    if connection is None:
        with get_sqlite_connection() as conn:
            return editar_titular(titular_id, nome, telefone, email, connection=conn, usuario_id=usuario_id)

    titular_atual = executar_query(
        "SELECT nome, telefone, email FROM titulares WHERE id = ?",
        [titular_id],
        fetch_one=True,
        connection=connection,
    )
    if not titular_atual:
        return False

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    nome_anterior = titular_atual['nome']

    executar_query(
        "UPDATE titulares SET nome = ?, telefone = ?, email = ?, updated_at = ? WHERE id = ?",
        [nome, telefone, email, now, titular_id],
        connection=connection,
    )

    _sincronizar_processos_cadastro(
        cadastro_id=titular_id,
        nome_anterior=nome_anterior,
        nome_novo=nome,
        telefone_novo=telefone,
        email_novo=email,
        tipo_cadastro='titular',
        usuario_id=usuario_id,
        connection=connection,
    )
    return True

def excluir_titular(titular_id, connection=None):
    """Exclui um titular sem processos vinculados."""
    rows = executar_query("DELETE FROM titulares WHERE id = ?", [titular_id], connection=connection)
    return rows

def get_historico_servicos_titular(titular_id_ou_nome):
    """Obtém o histórico por titular_id, com fallback para processos legados."""
    if isinstance(titular_id_ou_nome, int):
        where_sql = "p.titular_id = ? OR (p.titular_id IS NULL AND p.titular = (SELECT nome FROM titulares WHERE id = ?))"
        params = [titular_id_ou_nome, titular_id_ou_nome]
    else:
        where_sql = "p.titular = ?"
        params = [titular_id_ou_nome]

    query = f"""
        SELECT p.*, ts.nome as tipo_servico_nome, sp.nome as status_nome, sp.hex_color
        FROM processos p
        JOIN tipos_servico ts ON p.tipo_id = ts.id
        JOIN status_processo sp ON p.status_id = sp.id
        WHERE {where_sql}
        ORDER BY p.data_entrada DESC
    """
    return executar_query(query, params, fetch_all=True)

def upsert_titular_from_processo(titular_nome, telefone, email, processo_id, connection=None, nome_anterior=None, cadastro_id=None, usuario_id=None, processo_excluido_id=None):
    """Cria ou atualiza um titular sem duplicar quando um processo é renomeado."""
    from datetime import datetime
    if not titular_nome:
        return None
    if connection is None:
        with get_sqlite_connection() as conn:
            return upsert_titular_from_processo(
                titular_nome,
                telefone,
                email,
                processo_id,
                connection=conn,
                nome_anterior=nome_anterior,
                cadastro_id=cadastro_id,
                usuario_id=usuario_id,
                processo_excluido_id=processo_excluido_id,
            )
        
    # O ID é a identidade principal. Assim, editar nome, telefone ou e-mail
    # pelo processo altera o cadastro original, mesmo que o nome tenha mudado.
    titular = None
    if cadastro_id:
        titular = executar_query(
            "SELECT id, nome, telefone, email FROM titulares WHERE id = ?",
            [cadastro_id],
            fetch_one=True,
            connection=connection,
        )

    if titular is None:
        titular = executar_query(
            "SELECT id, nome, telefone, email FROM titulares WHERE nome = ?",
            [titular_nome],
            fetch_one=True,
            connection=connection,
        )
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if titular:
        # Buscar dados atuais para não sobrescrever com vazio
        titular_atual = executar_query("SELECT telefone, email FROM titulares WHERE id = ?", [titular['id']], fetch_one=True, connection=connection)
        
        novo_telefone = telefone if telefone else titular_atual['telefone']
        novo_email = email if email else titular_atual['email']
        
        # Atualizar dados existentes
        query_update = """
            UPDATE titulares 
            SET telefone = ?, email = ?, ultimo_registro_id = ?, updated_at = ? 
            WHERE id = ?
        """
        nome_atual = titular.get('nome') or titular_nome
        nome_final = titular_nome if cadastro_id else nome_atual
        executar_query(
            "UPDATE titulares SET nome = ?, telefone = ?, email = ?, ultimo_registro_id = ?, updated_at = ? WHERE id = ?",
            [nome_final, novo_telefone, novo_email, processo_id, now, titular['id']],
            connection=connection,
        )
        _sincronizar_processos_cadastro(
            cadastro_id=titular['id'],
            nome_anterior=nome_atual,
            nome_novo=nome_final,
            telefone_novo=novo_telefone,
            email_novo=novo_email,
            tipo_cadastro='titular',
            usuario_id=usuario_id,
            processo_excluido_id=processo_excluido_id,
            connection=connection,
        )
        return titular['id']
    else:
        # Se o nome anterior pertencia exclusivamente a este processo, trata a
        # alteração como edição do mesmo cadastro. Quando o nome antigo está
        # compartilhado por outros processos, cria-se um novo cadastro apenas
        # para este processo, preservando os demais vínculos.
        if nome_anterior and nome_anterior != titular_nome:
            titular_anterior = executar_query(
                "SELECT id FROM titulares WHERE nome = ?",
                [nome_anterior],
                fetch_one=True,
                connection=connection,
            )
            if titular_anterior:
                total_processos = executar_query(
                    """
                    SELECT COUNT(*) AS total
                      FROM processos
                     WHERE titular_id = ?
                        OR (titular_id IS NULL AND titular = ?)
                    """,
                    [titular_anterior['id'], nome_anterior],
                    fetch_one=True,
                    connection=connection,
                )
                if total_processos and total_processos['total'] <= 1:
                    executar_query(
                        """
                        UPDATE titulares
                           SET nome = ?, telefone = ?, email = ?, ultimo_registro_id = ?, updated_at = ?
                         WHERE id = ?
                        """,
                        [titular_nome, telefone, email, processo_id, now, titular_anterior['id']],
                        connection=connection,
                    )
                    _sincronizar_processos_cadastro(
                        cadastro_id=titular_anterior['id'],
                        nome_anterior=nome_anterior,
                        nome_novo=titular_nome,
                        telefone_novo=telefone,
                        email_novo=email,
                        tipo_cadastro='titular',
                        usuario_id=usuario_id,
                        processo_excluido_id=processo_excluido_id,
                        connection=connection,
                    )
                    return titular_anterior['id']

        # Inserir novo titular
        query_insert = """
            INSERT INTO titulares (nome, telefone, email, ultimo_registro_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor = connection.cursor()
        cursor.execute(query_insert, [titular_nome, telefone, email, processo_id, now, now])
        return cursor.lastrowid

def buscar_titulares_json(termo):
    """Busca titulares para o dropdown de pesquisa (AJAX). '%' lista todos."""
    if termo.strip() == '%':
        query = "SELECT id, nome, telefone, email FROM titulares ORDER BY nome ASC LIMIT 50"
        return executar_query(query, [], fetch_all=True)
    query = "SELECT id, nome, telefone, email FROM titulares WHERE nome LIKE ? OR email LIKE ? ORDER BY nome ASC LIMIT 20"
    like = f"%{termo}%"
    return executar_query(query, [like, like], fetch_all=True)

def listar_apresentantes(filtros=None, pagina=1, registros_por_pagina=10):
    """Lista apresentantes com paginação e filtros."""
    import math
    offset = (pagina - 1) * registros_por_pagina
    
    query = """SELECT r.*,
               ultimo.id as ultimo_registro_id,
               CASE WHEN ultimo.id IS NULL THEN NULL
                    WHEN (ultimo.possui_matricula = 1 OR (ultimo.possui_matricula IS NULL AND ultimo.matricula IS NOT NULL)) AND ultimo.matricula IS NOT NULL THEN ultimo.matricula
                    ELSE 'Sem Matrícula'
               END as ultimo_registro_matricula,
               (SELECT COUNT(*) FROM processos pr
                  WHERE pr.apresentante_id = r.id
                     OR (pr.apresentante_id IS NULL AND pr.apresentante = r.nome)) as total_processos
               FROM apresentantes r
               LEFT JOIN processos ultimo ON ultimo.id = (
                   SELECT pr_last.id FROM processos pr_last
                    WHERE pr_last.apresentante_id = r.id
                       OR (pr_last.apresentante_id IS NULL AND pr_last.apresentante = r.nome)
                    ORDER BY pr_last.data_entrada DESC, pr_last.id DESC
                    LIMIT 1
               )
               WHERE 1=1"""
    params = []
    
    if filtros:
        if filtros.get('busca'):
            query += " AND (r.nome LIKE ? OR r.email LIKE ? OR r.telefone LIKE ?)"
            busca = f"%{filtros['busca']}%"
            params.extend([busca, busca, busca])
            
    count_query = f"SELECT COUNT(*) FROM ({query})"
    total_records = executar_query(count_query, params, fetch_one=True)['COUNT(*)']
    
    ordenar = filtros.get('ordenar', 'nome') if filtros else 'nome'
    direcao = filtros.get('direcao', 'asc') if filtros else 'asc'
    
    colunas_validas = {'id': 'r.id', 'nome': 'r.nome', 'email': 'r.email', 'telefone': 'r.telefone', 'processos': 'total_processos'}
    col_sql = colunas_validas.get(ordenar, 'r.nome')
    dir_sql = 'DESC' if direcao == 'desc' else 'ASC'
    
    query += f" ORDER BY {col_sql} {dir_sql} LIMIT ? OFFSET ?"
    params.extend([registros_por_pagina, offset])
    
    apresentantes = executar_query(query, params, fetch_all=True)
    
    return {
        'apresentantes': apresentantes,
        'total_records': total_records,
        'total_pages': math.ceil(total_records / registros_por_pagina) if total_records > 0 else 0
    }

def get_apresentante_by_id(apresentante_id):
    """Obtém detalhes de um apresentante pelo ID."""
    query = """SELECT r.*,
               ultimo.id as ultimo_registro_id,
               CASE WHEN ultimo.id IS NULL THEN NULL
                    WHEN (ultimo.possui_matricula = 1 OR (ultimo.possui_matricula IS NULL AND ultimo.matricula IS NOT NULL)) AND ultimo.matricula IS NOT NULL THEN ultimo.matricula
                    ELSE 'Sem Matrícula'
               END as ultimo_registro_matricula,
               (SELECT COUNT(*) FROM processos pr
                  WHERE pr.apresentante_id = r.id
                     OR (pr.apresentante_id IS NULL AND pr.apresentante = r.nome)) as total_processos
               FROM apresentantes r
               LEFT JOIN processos ultimo ON ultimo.id = (
                   SELECT pr_last.id FROM processos pr_last
                    WHERE pr_last.apresentante_id = r.id
                       OR (pr_last.apresentante_id IS NULL AND pr_last.apresentante = r.nome)
                    ORDER BY pr_last.data_entrada DESC, pr_last.id DESC
                    LIMIT 1
               )
               WHERE r.id = ?"""
    return executar_query(query, [apresentante_id], fetch_one=True)

def apresentante_tem_processos(apresentante_id):
    """Verifica vínculo por ID e mantém fallback para processos legados."""
    rep = executar_query("SELECT nome FROM apresentantes WHERE id = ?", [apresentante_id], fetch_one=True)
    if not rep:
        return False
    result = executar_query(
        """
        SELECT COUNT(*) AS cnt
          FROM processos
         WHERE apresentante_id = ?
            OR (apresentante_id IS NULL AND apresentante = ?)
        """,
        [apresentante_id, rep['nome']],
        fetch_one=True,
    )
    return result['cnt'] > 0 if result else False

def editar_apresentante(apresentante_id, nome, telefone, email, connection=None, usuario_id=None):
    """Atualiza um apresentante e sincroniza os processos vinculados pelo nome."""
    from datetime import datetime

    if connection is None:
        with get_sqlite_connection() as conn:
            return editar_apresentante(apresentante_id, nome, telefone, email, connection=conn, usuario_id=usuario_id)

    apresentante_atual = executar_query(
        "SELECT nome, telefone, email FROM apresentantes WHERE id = ?",
        [apresentante_id],
        fetch_one=True,
        connection=connection,
    )
    if not apresentante_atual:
        return False

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    nome_anterior = apresentante_atual['nome']

    executar_query(
        "UPDATE apresentantes SET nome = ?, telefone = ?, email = ?, updated_at = ? WHERE id = ?",
        [nome, telefone, email, now, apresentante_id],
        connection=connection,
    )
    _sincronizar_processos_cadastro(
        cadastro_id=apresentante_id,
        nome_anterior=nome_anterior,
        nome_novo=nome,
        telefone_novo=telefone,
        email_novo=email,
        tipo_cadastro='apresentante',
        usuario_id=usuario_id,
        connection=connection,
    )
    return True

def excluir_apresentante(apresentante_id, connection=None):
    """Exclui um apresentante sem processos vinculados."""
    rows = executar_query("DELETE FROM apresentantes WHERE id = ?", [apresentante_id], connection=connection)
    return rows

def get_historico_servicos_apresentante(apresentante_id_ou_nome):
    """Obtém o histórico por apresentante_id, com fallback para processos legados."""
    if isinstance(apresentante_id_ou_nome, int):
        where_sql = "p.apresentante_id = ? OR (p.apresentante_id IS NULL AND p.apresentante = (SELECT nome FROM apresentantes WHERE id = ?))"
        params = [apresentante_id_ou_nome, apresentante_id_ou_nome]
    else:
        where_sql = "p.apresentante = ?"
        params = [apresentante_id_ou_nome]

    query = f"""
        SELECT p.*, ts.nome as tipo_servico_nome, sp.nome as status_nome, sp.hex_color
        FROM processos p
        JOIN tipos_servico ts ON p.tipo_id = ts.id
        JOIN status_processo sp ON p.status_id = sp.id
        WHERE {where_sql}
        ORDER BY p.data_entrada DESC
    """
    return executar_query(query, params, fetch_all=True)

def buscar_apresentantes_json(termo):
    """Busca apresentantes para o dropdown de pesquisa (AJAX). '%' lista todos."""
    if termo.strip() == '%':
        query = "SELECT id, nome, telefone, email FROM apresentantes ORDER BY nome ASC LIMIT 50"
        return executar_query(query, [], fetch_all=True)
    query = "SELECT id, nome, telefone, email FROM apresentantes WHERE nome LIKE ? OR email LIKE ? ORDER BY nome ASC LIMIT 20"
    like = f"%{termo}%"
    return executar_query(query, [like, like], fetch_all=True)

def upsert_apresentante_from_processo(apresentante_nome, telefone, email, processo_id, connection=None, nome_anterior=None, cadastro_id=None, usuario_id=None, processo_excluido_id=None):
    """Cria ou atualiza um apresentante sem duplicar quando um processo é renomeado."""
    from datetime import datetime
    if not apresentante_nome:
        return None
    if connection is None:
        with get_sqlite_connection() as conn:
            return upsert_apresentante_from_processo(
                apresentante_nome,
                telefone,
                email,
                processo_id,
                connection=conn,
                nome_anterior=nome_anterior,
                cadastro_id=cadastro_id,
                usuario_id=usuario_id,
                processo_excluido_id=processo_excluido_id,
            )
        
    # O ID é a identidade principal. Assim, editar nome, telefone ou e-mail
    # pelo processo altera o cadastro original, mesmo que o nome tenha mudado.
    apresentante = None
    if cadastro_id:
        apresentante = executar_query(
            "SELECT id, nome, telefone, email FROM apresentantes WHERE id = ?",
            [cadastro_id],
            fetch_one=True,
            connection=connection,
        )

    if apresentante is None:
        apresentante = executar_query(
            "SELECT id, nome, telefone, email FROM apresentantes WHERE nome = ?",
            [apresentante_nome],
            fetch_one=True,
            connection=connection,
        )
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if apresentante:
        apresentante_atual = executar_query("SELECT telefone, email FROM apresentantes WHERE id = ?", [apresentante['id']], fetch_one=True, connection=connection)
        
        novo_telefone = telefone if telefone else apresentante_atual['telefone']
        novo_email = email if email else apresentante_atual['email']
        
        query_update = """
            UPDATE apresentantes 
            SET telefone = ?, email = ?, updated_at = ? 
            WHERE id = ?
        """
        nome_atual = apresentante.get('nome') or apresentante_nome
        nome_final = apresentante_nome if cadastro_id else nome_atual
        executar_query(
            "UPDATE apresentantes SET nome = ?, telefone = ?, email = ?, updated_at = ? WHERE id = ?",
            [nome_final, novo_telefone, novo_email, now, apresentante['id']],
            connection=connection,
        )
        _sincronizar_processos_cadastro(
            cadastro_id=apresentante['id'],
            nome_anterior=nome_atual,
            nome_novo=nome_final,
            telefone_novo=novo_telefone,
            email_novo=novo_email,
            tipo_cadastro='apresentante',
            usuario_id=usuario_id,
            processo_excluido_id=processo_excluido_id,
            connection=connection,
        )
        return apresentante['id']
    else:
        if nome_anterior and nome_anterior != apresentante_nome:
            apresentante_anterior = executar_query(
                "SELECT id FROM apresentantes WHERE nome = ?",
                [nome_anterior],
                fetch_one=True,
                connection=connection,
            )
            if apresentante_anterior:
                total_processos = executar_query(
                    """
                    SELECT COUNT(*) AS total
                      FROM processos
                     WHERE apresentante_id = ?
                        OR (apresentante_id IS NULL AND apresentante = ?)
                    """,
                    [apresentante_anterior['id'], nome_anterior],
                    fetch_one=True,
                    connection=connection,
                )
                if total_processos and total_processos['total'] <= 1:
                    executar_query(
                        """
                        UPDATE apresentantes
                           SET nome = ?, telefone = ?, email = ?, updated_at = ?
                         WHERE id = ?
                        """,
                        [apresentante_nome, telefone, email, now, apresentante_anterior['id']],
                        connection=connection,
                    )
                    _sincronizar_processos_cadastro(
                        cadastro_id=apresentante_anterior['id'],
                        nome_anterior=nome_anterior,
                        nome_novo=apresentante_nome,
                        telefone_novo=telefone,
                        email_novo=email,
                        tipo_cadastro='apresentante',
                        usuario_id=usuario_id,
                        processo_excluido_id=processo_excluido_id,
                        connection=connection,
                    )
                    return apresentante_anterior['id']

        query_insert = """
            INSERT INTO apresentantes (nome, telefone, email, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor = connection.cursor()
        cursor.execute(query_insert, [apresentante_nome, telefone, email, now, now])
        return cursor.lastrowid

