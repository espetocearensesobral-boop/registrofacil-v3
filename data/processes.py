"""Serviços de processos, histórico e anexos.

As funções preservam as assinaturas legadas, incluindo o parâmetro
`connection` usado por operações transacionais.
"""

import sqlite3
from datetime import datetime

from config import Config
from data.backup import rebuild_fts_index
from data.database import executar_query, get_sqlite_connection
from utils.logger import operacional_logger as logger

DATABASE_PATH = Config.DATABASE_PATH

def validar_status(status_nome):
    if not status_nome:
        raise ValueError("Nome do status não pode ser vazio.")
    result = executar_query("SELECT id FROM status_processo WHERE nome = ? AND ativo = 1", [status_nome], fetch_one=True)
    if not result:
        raise ValueError(f"Status '{status_nome}' inválido, não encontrado ou inativo.")
    return True

def get_status_id_by_name(status_name):
    result = executar_query("SELECT id FROM status_processo WHERE nome = ?", [status_name], fetch_one=True)
    return result['id'] if result else None

def create_processo(numero_processo, titular, titular_telefone, titular_email, matricula, tipo_id, data_entrada, status_id, prazo_final, apresentante, apresentante_telefone, apresentante_email, responsavel_id, envolvido_notas, observacoes, data_conclusao, possui_matricula=0, connection=None, titular_id=None, apresentante_id=None):
    try:
        query = """
            INSERT INTO processos (numero_processo, titular, titular_id, titular_telefone, titular_email, matricula, possui_matricula, tipo_id, data_entrada, status_id,
                                   prazo_final, apresentante, apresentante_id, apresentante_telefone, apresentante_email,
                                   responsavel_id, envolvido_notas, observacoes, data_conclusao,
                                   created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """
        formatted_data_entrada = data_entrada
        formatted_prazo_final = prazo_final
        formatted_data_conclusao = data_conclusao
        # Se não possui matrícula, garantir que o valor seja NULL
        matricula_final = matricula if possui_matricula else None

        params = [
            numero_processo, titular, titular_id, titular_telefone, titular_email, matricula_final, possui_matricula, tipo_id, formatted_data_entrada, status_id,
            formatted_prazo_final, apresentante, apresentante_id, apresentante_telefone, apresentante_email,
            responsavel_id, envolvido_notas, observacoes, formatted_data_conclusao
        ]
        
        cursor = connection.cursor()
        cursor.execute(query, params)
        processo_id = cursor.lastrowid
        
        registrar_historico_processo(
            processo_id=processo_id,
            usuario_id=responsavel_id,
            campo_alterado='criacao',
            valor_antigo=None,
            valor_novo=f"Processo criado: {titular}",
            observacao_adicional=f"Processo ID {processo_id} criado.",
            connection=connection
        )
        
        logger.info(f"Processo '{numero_processo}' criado com sucesso no DB com ID: {processo_id}.")
        return processo_id
    except sqlite3.IntegrityError as e:
        logger.warning(f"Tentativa de criar processo com número '{numero_processo}' já existente. Erro: {e}")
        raise ValueError("Erro de integridade ao criar processo.") from e
    except Exception as e:
        logger.error(f"Erro ao criar processo '{numero_processo}': {e}", exc_info=True)
        raise

def get_processo_by_id(processo_id):
    query = """
        SELECT
            P.id, P.numero_processo, P.titular, P.titular_id, P.titular_telefone, P.titular_email, P.matricula, P.possui_matricula, P.tipo_id,
            P.data_entrada, P.status_id, P.prazo_final, P.apresentante, P.apresentante_id,
            P.apresentante_telefone, P.apresentante_email, P.responsavel_id,
            P.envolvido_notas, P.observacoes, P.data_conclusao, P.created_at, P.updated_at,
            TS.nome AS tipo_nome, TS.prazo_padrao, SP.nome AS status_nome_original, SP.hex_color AS status_hex_original,
            U.nome AS responsavel_nome
        FROM processos P
        JOIN tipos_servico TS ON P.tipo_id = TS.id
        JOIN status_processo SP ON P.status_id = SP.id
        LEFT JOIN usuarios U ON P.responsavel_id = U.id
        WHERE P.id = ?
    """
    return executar_query(query, [processo_id], fetch_one=True)

def update_processo(processo_id, titular, titular_telefone, titular_email, matricula, tipo_id, data_entrada, status_id, prazo_final, apresentante, apresentante_telefone, apresentante_email, responsavel_id, envolvido_notas, observacoes, data_conclusao, possui_matricula=0, connection=None, titular_id=None, apresentante_id=None, expected_updated_at=None):
    try:
        old_processo_data = get_processo_by_id(processo_id)
        if not old_processo_data:
            raise ValueError(f"Processo com ID {processo_id} não encontrado para atualização.")

        formatted_data_entrada = data_entrada
        formatted_prazo_final = prazo_final
        formatted_data_conclusao = data_conclusao
        # Se não possui matrícula, garantir que o valor seja NULL
        matricula_final = matricula if possui_matricula else None

        query = """
            UPDATE processos SET
            titular = ?, titular_id = ?, titular_telefone = ?, titular_email = ?, matricula = ?, possui_matricula = ?, tipo_id = ?, data_entrada = ?, status_id = ?,
            prazo_final = ?, apresentante = ?, apresentante_id = ?, apresentante_telefone = ?, apresentante_email = ?,
            responsavel_id = ?, envolvido_notas = ?, observacoes = ?, data_conclusao = ?,
            updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
            WHERE id = ?
        """
        params = [
            titular, titular_id, titular_telefone, titular_email, matricula_final, possui_matricula, tipo_id, formatted_data_entrada, status_id,
            formatted_prazo_final, apresentante, apresentante_id, apresentante_telefone, apresentante_email,
            responsavel_id, envolvido_notas, observacoes, formatted_data_conclusao,
            processo_id
        ]
        if expected_updated_at:
            query = query.replace("WHERE id = ?", "WHERE id = ? AND updated_at = ?")
            params.append(expected_updated_at)

        cursor = connection.cursor()

        # Tentativa 1: UPDATE normal (trigger FTS dispara automaticamente)
        try:
            cursor.execute(query, params)
        except sqlite3.DatabaseError as db_err:
            err_msg = str(db_err).lower()
            # Se o erro vier do trigger FTS (malformed/corrupt), reconstruir FTS e tentar novamente
            if 'malformed' in err_msg or 'corrupt' in err_msg or 'disk image' in err_msg:
                logger.warning(
                    f"FTS5 corrompido detectado durante update_processo({processo_id}). "
                    "Reconstruindo índice FTS e tentando novamente..."
                )
                # Commit parcial para liberar a transação travada
                try:
                    connection.rollback()
                except Exception:
                    pass

                # Reconstruir FTS usando nova conexão independente
                try:
                    rebuild_fts_index()
                    logger.info("FTS5 reconstruído com sucesso. Tentando UPDATE novamente.")
                except Exception as rebuild_err:
                    logger.error(f"Falha ao reconstruir FTS5: {rebuild_err}")

                # Tentativa 2: UPDATE sem trigger (drop trigger temporariamente)
                try:
                    cursor2 = connection.cursor()
                    # Desabilitar triggers FTS temporariamente para este UPDATE
                    cursor2.execute("DROP TRIGGER IF EXISTS processos_fts_update")
                    cursor2.execute(query, params)
                    logger.info(f"UPDATE do processo {processo_id} concluído sem trigger FTS.")
                    # Recriar o trigger correto
                    cursor2.execute("""
                        CREATE TRIGGER IF NOT EXISTS processos_fts_update
                        AFTER UPDATE ON processos BEGIN
                            DELETE FROM processos_fts WHERE rowid = old.id;
                            INSERT INTO processos_fts(rowid, numero_processo, titular, matricula, apresentante, observacoes)
                            VALUES (new.id, new.numero_processo, new.titular, new.matricula, new.apresentante, new.observacoes);
                        END
                    """)
                    cursor = cursor2
                except Exception as retry_err:
                    logger.error(f"Tentativa 2 de UPDATE também falhou: {retry_err}")
                    raise sqlite3.DatabaseError(
                        f"Falha persistente ao salvar processo mesmo após reconstrução do FTS. "
                        f"Erro original: {db_err}. Erro na segunda tentativa: {retry_err}"
                    )
            else:
                raise
        rows_affected = cursor.rowcount
        if expected_updated_at and not rows_affected:
            raise ValueError("Este processo foi alterado por outro usuário. Recarregue a tela antes de salvar.")

        if rows_affected:
            current_data = {
                'titular': titular,
                'matricula': matricula_final,
                'possui_matricula': possui_matricula,
                'tipo_id': tipo_id,
                'data_entrada': formatted_data_entrada,
                'status_id': status_id,
                'prazo_final': formatted_prazo_final,
                'apresentante': apresentante,
                'apresentante_telefone': apresentante_telefone,
                'apresentante_email': apresentante_email,
                'responsavel_id': responsavel_id,
                'envolvido_notas': envolvido_notas,
                'observacoes': observacoes,
                'data_conclusao': data_conclusao
            }
            tipo_nome_antigo = executar_query("SELECT nome FROM tipos_servico WHERE id = ?", [old_processo_data['tipo_id']], fetch_one=True, connection=connection)['nome'] if old_processo_data['tipo_id'] else None
            tipo_nome_novo = executar_query("SELECT nome FROM tipos_servico WHERE id = ?", [tipo_id], fetch_one=True, connection=connection)['nome'] if tipo_id else None

            status_nome_antigo = executar_query("SELECT nome FROM status_processo WHERE id = ?", [old_processo_data['status_id']], fetch_one=True, connection=connection)['nome'] if old_processo_data['status_id'] else None
            status_nome_novo = executar_query("SELECT nome FROM status_processo WHERE id = ?", [status_id], fetch_one=True, connection=connection)['nome'] if status_id else None
            
            responsavel_nome_antigo = executar_query("SELECT nome FROM usuarios WHERE id = ?", [old_processo_data['responsavel_id']], fetch_one=True, connection=connection)['nome'] if old_processo_data['responsavel_id'] else None
            responsavel_nome_novo = executar_query("SELECT nome FROM usuarios WHERE id = ?", [responsavel_id], fetch_one=True, connection=connection)['nome'] if responsavel_id else None

            field_display_names = {
                'titular': 'Titular', 'matricula': 'Matrícula', 'tipo_id': 'Tipo de Serviço',
                'data_entrada': 'Data de Entrada', 'status_id': 'Status', 'prazo_final': 'Prazo Final',
                'apresentante': 'Apresentante', 'apresentante_telefone': 'Telefone Apresentante',
                'apresentante_email': 'E-mail Apresentante', 'responsavel_id': 'Responsável',
                'envolvido_notas': 'Envolve Notas', 'observacoes': 'Observações', 'data_conclusao': 'Data de Conclusão'
            }

            for field, display_name in field_display_names.items():
                old_value = old_processo_data.get(field)
                new_value = current_data.get(field)

                old_value_display = old_value
                new_value_display = new_value

                if field == 'tipo_id':
                    old_value_display = tipo_nome_antigo
                    new_value_display = tipo_nome_novo
                elif field == 'status_id':
                    old_value_display = status_nome_antigo
                    new_value_display = status_nome_novo
                elif field == 'responsavel_id':
                    old_value_display = responsavel_nome_antigo
                    new_value_display = responsavel_nome_novo
                elif field == 'envolvido_notas':
                    old_value_display = "Sim" if old_value else "Não"
                    new_value_display = "Sim" if new_value else "Não"
                elif field in ['data_entrada', 'prazo_final', 'data_conclusao']:
                    if isinstance(old_value, str) and old_value:
                        try:
                            old_value_display = datetime.strptime(old_value.split(' ')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
                        except ValueError:
                            old_value_display = old_value
                    if isinstance(new_value, str) and new_value:
                        try:
                            new_value_display = datetime.strptime(new_value.split(' ')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
                        except ValueError:
                            new_value_display = new_value
                        
                if str(old_value_display or '').strip() != str(new_value_display or '').strip():
                    registrar_historico_processo(
                        processo_id=processo_id,
                        usuario_id=responsavel_id,
                        campo_alterado=display_name,
                        valor_antigo=str(old_value_display) if old_value_display is not None else "",
                        valor_novo=str(new_value_display) if new_value_display is not None else "",
                        connection=connection
                    )
            
            logger.info(f"Processo '{processo_id}' atualizado com sucesso no DB.")
        return rows_affected
    except sqlite3.IntegrityError as e:
        logger.warning(f"Tentativa de atualizar processo '{processo_id}' com erro de integridade. Erro: {e}")
        raise ValueError("Erro de integridade ao atualizar processo.") from e
    except Exception as e:
        logger.error(f"Erro ao atualizar processo '{processo_id}': {e}", exc_info=True)
        raise

def excluir_processo_db(processo_id, connection):
    """
    Exclui um processo e mantém o titular desvinculado (sem perda de dados do titular).
    """
    try:
        # Desvincula o titular explicitamente (caso FK não propague em todas versões do SQLite)
        executar_query(
            "UPDATE titulares SET ultimo_registro_id = NULL, updated_at = strftime('%Y-%m-%d %H:%M:%S','now','localtime') WHERE ultimo_registro_id = ?",
            [processo_id], connection=connection
        )

        rows_affected = executar_query(
            "DELETE FROM processos WHERE id = ?",
            [processo_id],
            connection=connection
        )
        
        if rows_affected > 0:
            logger.info(f"Processo ID {processo_id} excluído com sucesso da tabela 'processos'.")
            return True
        else:
            logger.warning(f"Tentativa de excluir o processo ID {processo_id}, mas não foi encontrado.")
            return False

    except Exception as e:
        logger.error(f"Erro no modelo ao excluir o processo ID {processo_id}: {e}", exc_info=True)
        raise e

def registrar_historico_processo(processo_id, usuario_id, campo_alterado, valor_antigo, valor_novo, observacao_adicional=None, connection=None):
    if connection:
        conn = connection
        close_conn = False
    else:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        close_conn = True

    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO historico_processos (processo_id, usuario_id, campo_alterado, valor_antigo, valor_novo, observacao_adicional, timestamp_alteracao)
            VALUES (?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """
        cursor.execute(query, [processo_id, usuario_id, campo_alterado, valor_antigo, valor_novo, observacao_adicional])
        if close_conn:
            conn.commit()
        logger.debug(f"Histórico registrado para processo {processo_id}: Campo '{campo_alterado}', Antigo: '{valor_antigo}', Novo: '{valor_novo}', Obs: '{observacao_adicional}'")
    except Exception as e:
        logger.error(f"Erro ao registrar histórico para processo {processo_id}: {e}", exc_info=True)
        if close_conn:
            conn.rollback()
        raise
    finally:
        if close_conn:
            conn.close()

def obter_historico_processo(processo_id):
    query = """
        SELECT
            hp.id,
            hp.processo_id,
            hp.usuario_id,
            hp.campo_alterado,
            hp.valor_antigo,
            hp.valor_novo,
            hp.observacao_adicional,
            hp.timestamp_alteracao,
            U.nome AS usuario_nome
        FROM
            historico_processos hp
        LEFT JOIN
            usuarios U ON hp.usuario_id = U.id
        WHERE
            hp.processo_id = ?
        ORDER BY
            hp.timestamp_alteracao DESC, hp.id DESC
    """
    return executar_query(query, [processo_id], fetch_all=True)

def listar_processos(filtros, pagina_atual, registros_por_pagina, ordenar, ignore_default_filters=False): # MODIFICADO: Adicionado ignore_default_filters
    base_query = """
        SELECT
            P.id, P.numero_processo, P.titular, P.titular_telefone, P.titular_email,
            P.apresentante, P.apresentante_telefone, P.apresentante_email, P.matricula,
            P.data_entrada, P.prazo_final, P.envolvido_notas,
            TS.nome AS tipo_nome,
            SP.nome AS status_nome, SP.hex_color AS status_hex,
            U.nome AS responsavel_nome
        FROM
            processos P
        JOIN
            tipos_servico TS ON P.tipo_id = TS.id
        JOIN
            status_processo SP ON P.status_id = SP.id
        LEFT JOIN
            usuarios U ON P.responsavel_id = U.id
    """
    count_query = "SELECT COUNT(P.id) AS total_count FROM processos P " \
                  "JOIN tipos_servico TS ON P.tipo_id = TS.id " \
                  "JOIN status_processo SP ON P.status_id = SP.id " \
                  "LEFT JOIN usuarios U ON P.responsavel_id = U.id "

    where_clauses = []
    query_params = []

    # MODIFICADO: Aplica filtros padrão APENAS SE ignore_default_filters for False
    if not ignore_default_filters:
        if filtros.get('status_id'):
            where_clauses.append("P.status_id = ?")
            query_params.append(filtros['status_id'])
        
        if 'status_ids_in' in filtros and filtros['status_ids_in']:
            placeholders = ','.join('?' * len(filtros['status_ids_in']))
            where_clauses.append(f"P.status_id IN ({placeholders})")
            query_params.extend(filtros['status_ids_in'])
        
        if filtros.get('filtro_pendentes_dashboard'):
            where_clauses.append("SP.nome LIKE '%Pendente%' AND SP.nome != 'Finalizado'")

        if filtros.get('filtro_em_andamento'):
            where_clauses.append("SP.nome != 'Finalizado' AND P.data_conclusao IS NULL")
        
        if filtros.get('responsavel_id'):
            where_clauses.append("P.responsavel_id = ?")
            query_params.append(filtros['responsavel_id'])
        
        # Note: Busca, data_inicio, data_fim, e envolve_notas são filtros manuais do usuário,
        # e geralmente são mantidos mesmo para 'suporte', a menos que a intenção seja *realmente* ver tudo.
        # Se a intenção é ignorar TUDO (incluindo busca), então essa lógica precisaria ser mais abrangente.
        # Por enquanto, assumirei que a busca manual e filtros de data/notas AINDA se aplicam se o suporte os usar.

    # ... (restante da função listar_processos) ...
    if filtros.get('tipo'):
        where_clauses.append("P.tipo_id = ?")
        query_params.append(filtros['tipo'])
    if filtros.get('matricula'):
        matricula_termo = f"%{filtros['matricula']}%"
        where_clauses.append("P.matricula LIKE ?")
        query_params.append(matricula_termo)
    if filtros.get('busca'):
        busca_termo = f"%{filtros['busca']}%"
        # A busca já contempla P.matricula LIKE ?, então a funcionalidade de pesquisar pelo número da matrícula já está presente na lógica de busca global.
        where_clauses.append("(P.numero_processo LIKE ? OR P.id LIKE ? OR P.titular LIKE ? OR P.titular_telefone LIKE ? OR P.titular_email LIKE ? OR P.apresentante LIKE ? OR P.apresentante_telefone LIKE ? OR P.apresentante_email LIKE ? OR P.matricula LIKE ? OR U.nome LIKE ? OR TS.nome LIKE ? OR SP.nome LIKE ?)")
        query_params.extend([busca_termo] * 12)
    if filtros.get('data_inicio'):
        where_clauses.append("P.data_entrada >= ?")
        query_params.append(filtros['data_inicio'])
    if filtros.get('data_fim'):
        where_clauses.append("P.data_entrada <= ?")
        query_params.append(filtros['data_fim'])
    if filtros.get('envolve_notas') is not None:
        where_clauses.append("P.envolvido_notas = ?")
        query_params.append(filtros['envolve_notas'])
    
    if where_clauses:
        base_query += " WHERE " + " AND ".join(where_clauses)
        count_query += " WHERE " + " AND ".join(where_clauses)

    order_map = {
        'data_entrada_asc': 'P.data_entrada ASC',
        'data_entrada_desc': 'P.data_entrada DESC',
        'titular_asc': 'P.titular COLLATE NOCASE ASC',
        'titular_desc': 'P.titular COLLATE NOCASE DESC',
        'tipo_asc': 'TS.nome COLLATE NOCASE ASC',
        'tipo_desc': 'TS.nome COLLATE NOCASE DESC',
        'status_asc': 'SP.nome COLLATE NOCASE ASC',
        'status_desc': 'SP.nome COLLATE NOCASE DESC',
        'id_asc': 'P.id ASC',
        'id_desc': 'P.id DESC',
        'matricula_asc': 'P.matricula COLLATE NOCASE ASC',
        'matricula_desc': 'P.matricula COLLATE NOCASE DESC',
        'prazo_asc': 'P.prazo_final ASC, P.id DESC',
        'prazo_desc': 'P.prazo_final DESC, P.id DESC',
    }
    order_by_clause = order_map.get(ordenar, 'P.id DESC')
    base_query += f" ORDER BY {order_by_clause}"

    offset = (pagina_atual - 1) * registros_por_pagina
    
    base_query += " LIMIT ? OFFSET ?"
    params_for_data_query = list(query_params)
    params_for_data_query.extend([registros_por_pagina, offset])

    total_registros_result = executar_query(count_query, query_params, fetch_one=True)
    total_records = total_registros_result['total_count'] if total_registros_result and 'total_count' in total_registros_result else 0
    total_pages = (total_records + registros_por_pagina - 1) // registros_por_pagina
    if total_pages == 0 and total_records > 0:
        total_pages = 1

    processos = executar_query(base_query, params_for_data_query, fetch_all=True)

    return {
        'processos': processos,
        'total_records': total_records,
        'total_pages': total_pages
    }

def get_total_processes_count():
    result = executar_query("SELECT COUNT(id) AS total_count FROM processos", fetch_one=True)
    return result['total_count'] if result and 'total_count' in result else 0

def get_concluidos_processes_count():
    """Conta processos com status 'Finalizado'."""
    result = executar_query(
        "SELECT COUNT(P.id) AS total_count FROM processos P JOIN status_processo SP ON P.status_id = SP.id WHERE SP.nome = 'Finalizado'",
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_overdue_processes_count():
    hoje = datetime.now().strftime('%Y-%m-%d')
    result = executar_query(
        "SELECT COUNT(P.id) AS total_count FROM processos P JOIN status_processo SP ON P.status_id = SP.id WHERE P.prazo_final < ? AND SP.nome != 'Finalizado'",
        [hoje],
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_in_progress_processes_count():
    """Conta processos com status 'Pendente%' e que não estão concluídos/arquivados/finalizados."""
    result = executar_query(
        "SELECT COUNT(P.id) AS total_count FROM processos P JOIN status_processo SP ON P.status_id = SP.id WHERE SP.nome LIKE 'Pendente%' AND SP.nome != 'Finalizado'",
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_today_processes_count():
    """Conta processos cuja data de entrada OU criação é hoje."""
    query = """
        SELECT COUNT(P.id) AS total_count FROM processos P
        WHERE strftime('%Y-%m-%d', P.data_entrada) = strftime('%Y-%m-%d', 'now', 'localtime')
           OR strftime('%Y-%m-%d', P.created_at)   = strftime('%Y-%m-%d', 'now', 'localtime')
    """
    result = executar_query(query, fetch_one=True)
    return result['total_count'] if result and 'total_count' in result else 0

def get_prenotados_processes_count():
    """Conta processos com status 'Prenotado'."""
    result = executar_query(
        """SELECT COUNT(P.id) AS total_count
           FROM processos P
           JOIN status_processo SP ON P.status_id = SP.id
           WHERE SP.nome = 'Prenotado'
             AND P.data_conclusao IS NULL""",
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_em_andamento_processes_count():
    """Conta todos os processos em andamento (não finalizados e sem data de conclusão)."""
    result = executar_query(
        """SELECT COUNT(P.id) AS total_count
           FROM processos P
           JOIN status_processo SP ON P.status_id = SP.id
           WHERE SP.nome != 'Finalizado'
             AND P.data_conclusao IS NULL""",
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_user_linked_processes_count(user_id):
    """Conta processos vinculados (responsável) ao usuário, excluindo finalizados/concluídos/arquivados."""
    result = executar_query(
        """SELECT COUNT(P.id) AS total_count
           FROM processos P
           JOIN status_processo SP ON P.status_id = SP.id
           WHERE P.responsavel_id = ?
             AND SP.nome != 'Finalizado'
             AND P.data_conclusao IS NULL""",
        [user_id],
        fetch_one=True
    )
    return result['total_count'] if result and 'total_count' in result else 0

def get_recent_processes(limit=5):
    """
    Retorna processos recentes, excluindo status 'Finalizado'.
    """
    query = """
        SELECT
            P.id, P.titular, P.matricula, P.data_entrada,
            SP.nome AS status_nome, SP.hex_color AS status_hex
        FROM
            processos P
        JOIN
            status_processo SP ON P.status_id = SP.id
        WHERE
            SP.nome != 'Finalizado'
        ORDER BY
            P.created_at DESC, P.id DESC
        LIMIT ?
    """
    return executar_query(query, [limit])

def get_critical_deadline_processes(limit=5):
    hoje = datetime.now().strftime('%Y-%m-%d')
    query = """
        SELECT
            P.id, P.titular, P.matricula, P.prazo_final,
            SP.nome AS status_nome, SP.hex_color AS status_hex,
            TS.nome AS tipo_servico_nome
        FROM
            processos P
        JOIN
            status_processo SP ON P.status_id = SP.id
        LEFT JOIN
            tipos_servico TS ON P.tipo_id = TS.id
        WHERE
            SP.nome != 'Finalizado'
            AND P.prazo_final IS NOT NULL
            AND (
                P.prazo_final < ? OR
                date(P.prazo_final) BETWEEN date('now', 'localtime') AND date('now', 'localtime', '+5 days')
            )
        ORDER BY
            CASE
                WHEN P.prazo_final < ? THEN 1
                WHEN P.prazo_final = ? THEN 2
                WHEN P.prazo_final > ? AND P.prazo_final <= date('now', 'localtime', '+5 days') THEN 3
                ELSE 4
            END,
            P.prazo_final ASC,
            P.titular COLLATE NOCASE ASC,
            P.id DESC
        LIMIT ?
    """
    results = executar_query(query, [hoje, hoje, hoje, hoje, limit])
    
    hoje_dt = datetime.now().date()
    for r in results:
        if isinstance(r['prazo_final'], str) and len(r['prazo_final']) >= 10:
            r['prazo_final_dt'] = datetime.strptime(r['prazo_final'].split(' ')[0], '%Y-%m-%d').date()
            r['prazo_diff_days'] = (r['prazo_final_dt'] - hoje_dt).days
            r['prazo_formatado'] = r['prazo_final_dt'].strftime('%d/%m/%Y')
        else:
            r['prazo_final_dt'] = None
            r['prazo_diff_days'] = None
            r['prazo_formatado'] = 'Sem prazo'
    return results

def get_dashboard_analytics():
    """Retorna indicadores agregados do Dashboard usando somente dados reais do sistema.

    A janela de movimentação considera os últimos sete dias, incluindo o dia atual.
    As consultas usam as tabelas existentes e retornam estruturas prontas para os
    cards e gráficos, sem gerar dados sintéticos.
    """
    daily_query = """
        SELECT * FROM (
            WITH RECURSIVE dias(dia) AS (
                SELECT date('now', 'localtime', '-6 days')
                UNION ALL
                SELECT date(dia, '+1 day') FROM dias
                WHERE dia < date('now', 'localtime')
            )
            SELECT
                dias.dia,
                COUNT(P.id) AS total
            FROM dias
            LEFT JOIN processos P
                ON date(COALESCE(NULLIF(P.data_entrada, ''), P.created_at)) = dias.dia
            GROUP BY dias.dia
            ORDER BY dias.dia ASC
        )
    """
    daily_rows = executar_query(daily_query, fetch_all=True) or []

    status_rows = executar_query(
        """
        SELECT SP.nome, SP.hex_color, COUNT(P.id) AS total
        FROM status_processo SP
        LEFT JOIN processos P ON P.status_id = SP.id
        GROUP BY SP.id, SP.nome, SP.hex_color
        HAVING COUNT(P.id) > 0
        ORDER BY total DESC, SP.nome COLLATE NOCASE ASC
        """,
        fetch_all=True,
    ) or []

    service_rows = executar_query(
        """
        SELECT COALESCE(TS.nome, 'Sem tipo') AS nome, COUNT(P.id) AS total
        FROM processos P
        LEFT JOIN tipos_servico TS ON P.tipo_id = TS.id
        GROUP BY P.tipo_id, TS.nome
        ORDER BY total DESC, nome COLLATE NOCASE ASC
        LIMIT 5
        """,
        fetch_all=True,
    ) or []

    summary = executar_query(
        """
        SELECT
            COUNT(P.id) AS total_processos,
            SUM(CASE WHEN SP.nome = 'Finalizado' OR P.data_conclusao IS NOT NULL THEN 1 ELSE 0 END) AS total_concluidos,
            SUM(CASE WHEN P.data_conclusao IS NULL AND SP.nome != 'Finalizado' THEN 1 ELSE 0 END) AS total_abertos,
            SUM(CASE WHEN P.data_conclusao IS NULL AND SP.nome != 'Finalizado' AND P.prazo_final < date('now', 'localtime') THEN 1 ELSE 0 END) AS total_vencidos,
            SUM(CASE WHEN P.data_conclusao IS NULL AND SP.nome != 'Finalizado' AND P.prazo_final = date('now', 'localtime') THEN 1 ELSE 0 END) AS total_vencem_hoje,
            SUM(CASE WHEN P.data_conclusao IS NULL AND SP.nome != 'Finalizado' AND P.prazo_final > date('now', 'localtime') AND P.prazo_final <= date('now', 'localtime', '+5 days') THEN 1 ELSE 0 END) AS total_proximos,
            SUM(CASE WHEN date(COALESCE(NULLIF(P.data_entrada, ''), P.created_at)) >= date('now', 'localtime', '-6 days') THEN 1 ELSE 0 END) AS movimentacao_7_dias
        FROM processos P
        JOIN status_processo SP ON P.status_id = SP.id
        """,
        fetch_one=True,
    ) or {}

    performance = executar_query(
        """
        SELECT
            COALESCE(ROUND(AVG(CASE
                WHEN P.data_conclusao IS NOT NULL
                 AND P.data_entrada IS NOT NULL
                 AND julianday(P.data_conclusao) >= julianday(P.data_entrada)
                THEN julianday(P.data_conclusao) - julianday(P.data_entrada)
            END), 1), 0) AS media_dias_conclusao,
            SUM(CASE
                WHEN P.data_conclusao IS NOT NULL
                 AND P.prazo_final IS NOT NULL
                 AND date(P.data_conclusao) <= date(P.prazo_final)
                THEN 1 ELSE 0
            END) AS concluidos_no_prazo,
            SUM(CASE WHEN P.data_conclusao IS NOT NULL OR SP.nome = 'Finalizado' THEN 1 ELSE 0 END) AS concluidos_com_data
        FROM processos P
        JOIN status_processo SP ON P.status_id = SP.id
        """,
        fetch_one=True,
    ) or {}

    daily = []
    for row in daily_rows:
        dia = row.get('dia')
        try:
            label = datetime.strptime(dia, '%Y-%m-%d').strftime('%d/%m')
        except (TypeError, ValueError):
            label = dia or '—'
        daily.append({'dia': dia, 'label': label, 'total': int(row.get('total') or 0)})

    total_processos = int(summary.get('total_processos') or 0)
    total_concluidos = int(summary.get('total_concluidos') or 0)
    concluidos_com_data = int(performance.get('concluidos_com_data') or 0)
    concluidos_no_prazo = int(performance.get('concluidos_no_prazo') or 0)
    pico = max(daily, key=lambda item: item['total'], default={'dia': None, 'label': '—', 'total': 0})

    return {
        'movimentacao_diaria': daily,
        'status_distribuicao': [
            {
                'nome': row.get('nome') or 'Sem status',
                'cor': row.get('hex_color') or '#6B7280',
                'total': int(row.get('total') or 0),
            }
            for row in status_rows
        ],
        'servicos_principais': [
            {'nome': row.get('nome') or 'Sem tipo', 'total': int(row.get('total') or 0)}
            for row in service_rows
        ],
        'total_processos': total_processos,
        'total_concluidos': total_concluidos,
        'total_abertos': int(summary.get('total_abertos') or 0),
        'total_vencidos': int(summary.get('total_vencidos') or 0),
        'total_vencem_hoje': int(summary.get('total_vencem_hoje') or 0),
        'total_proximos': int(summary.get('total_proximos') or 0),
        'movimentacao_7_dias': int(summary.get('movimentacao_7_dias') or 0),
        'pico_movimentacao': pico,
        'media_dias_conclusao': float(performance.get('media_dias_conclusao') or 0),
        'taxa_conclusao': round((total_concluidos / total_processos) * 100, 1) if total_processos else 0,
        'taxa_no_prazo': round((concluidos_no_prazo / concluidos_com_data) * 100, 1) if concluidos_com_data else 0,
    }


def obter_anexos_processo(processo_id):
    query = "SELECT id, nome_original, nome_arquivo, tipo, tamanho, data_upload FROM anexos_processos WHERE processo_id = ?"
    return executar_query(query, [processo_id])

def inserir_anexo_processo(processo_id, nome_original, nome_arquivo_servidor, mime_type, tamanho, usuario_upload_id, connection=None):
    query = """
        INSERT INTO anexos_processos
        (processo_id, nome_original, nome_arquivo, tipo, tamanho, data_upload, usuario_upload)
        VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), ?)
    """
    params = [processo_id, nome_original, nome_arquivo_servidor, mime_type, tamanho, usuario_upload_id]
    
    registrar_historico_processo(
        processo_id=processo_id,
        usuario_id=usuario_upload_id,
        campo_alterado='anexo',
        valor_antigo=None,
        valor_novo=nome_original,
        observacao_adicional=f"Anexo '{nome_original}' adicionado.",
        connection=connection
    )

    return executar_query(query, params, connection=connection)

def excluir_anexo_processo(anexo_id, processo_id, connection=None):
    query = "SELECT nome_arquivo, nome_original FROM anexos_processos WHERE id = ? AND processo_id = ?"
    result = executar_query(query, [anexo_id, processo_id], fetch_one=True, connection=connection)
    if result:
        rows_affected = executar_query("DELETE FROM anexos_processos WHERE id = ?", [anexo_id], connection=connection)
        if rows_affected:
            registrar_historico_processo(
                processo_id=processo_id,
                usuario_id=None,
                campo_alterado='anexo',
                valor_antigo=result['nome_original'],
                valor_novo=None,
                observacao_adicional=f"Anexo '{result['nome_original']}' removido.",
                connection=connection
            )
            return result['nome_arquivo']
    return None

