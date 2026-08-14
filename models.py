# registrofacil/models.py

import os
from datetime import datetime, timedelta
import math
import re
import uuid
import base64
import sqlite3
from contextlib import contextmanager
import pytz 
import secrets

from config import Config 
from utils.logger import logger, security_logger
from utils.helpers import validarCPF, validarCNPJ, validar_telefone, validar_email
from data.crypto import encrypt, decrypt


DATABASE_PATH = Config.DATABASE_PATH
TENTATIVAS_MAX = Config.TENTATIVAS_MAX
BLOQUEIO_TEMPO = Config.BLOQUEIO_TEMPO


UPLOAD_FOLDER = Config.UPLOAD_PROCESSOS_DIR  # Mantido para compatibilidade

MAX_FILE_SIZE = Config.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS

LOCK_TIMEOUT_MINUTES = 15

def validar_formato_matricula(matricula, processo_id=None):
    """
    Validação de matrícula: apenas formato, sem unicidade.
    Matrícula é opcional — se vazia/None, retorna True sem validar.

    Nota: 'processo_id' é aceito por compatibilidade de assinatura com os
    chamadores, mas não é usado aqui (não há checagem de duplicidade nesta
    função — apenas formato via regex).
    """
    if not matricula:
        return True  # Matrícula é opcional
    if not re.fullmatch(r'^[A-Za-z0-9\s\-\.\/]{1,50}$', matricula):
        raise ValueError("Matrícula inválida. Use apenas letras, números, espaços, hífens, pontos e barras (1-50 caracteres).")
    return True

def validar_telefone_unico(telefone, processo_id=None, titular_id=None, titular_nome=None):
    if not telefone: return True
    
    # Verificar em processos (apresentante_telefone)
    query_proc = "SELECT id FROM processos WHERE apresentante_telefone = ?"
    params_proc = [telefone]
    if processo_id:
        query_proc += " AND id != ?"
        params_proc.append(processo_id)
    
    # Se o titular_nome for fornecido, ignoramos processos do mesmo titular
    if titular_nome:
        query_proc += " AND titular != ?"
        params_proc.append(titular_nome)
    
    try:
        if executar_query(query_proc, params_proc, fetch_one=True):
            raise ValueError(f"TELEFONE: O telefone '{telefone}' já existe no sistema em outro processo de um titular diferente.")
            
        # Verificar em titulares
        query_tit = "SELECT id FROM titulares WHERE telefone = ?"
        params_tit = [telefone]
        
        # Se titular_nome for fornecido, tentamos achar o ID dele para ignorar na busca de duplicidade
        if titular_nome and not titular_id:
            tit_info = executar_query("SELECT id FROM titulares WHERE nome = ?", [titular_nome], fetch_one=True)
            if tit_info:
                titular_id = tit_info['id']

        # Se estamos editando um processo, precisamos encontrar se o titular vinculado a ele
        # é o mesmo que possui este telefone, para não dar falso positivo.
        titular_vinculado_id = None
        if processo_id:
            try:
                proc = executar_query("SELECT titular FROM processos WHERE id = ?", [processo_id], fetch_one=True)
                if proc:
                    tit = executar_query("SELECT id FROM titulares WHERE nome = ?", [proc['titular']], fetch_one=True)
                    if tit:
                        titular_vinculado_id = tit['id']
            except Exception as e:
                logger.error(f"Erro ao buscar titular vinculado para validação de telefone: {e}")

        target_titular_id = titular_id or titular_vinculado_id
        if target_titular_id:
            query_tit += " AND id != ?"
            params_tit.append(target_titular_id)
            
        if executar_query(query_tit, params_tit, fetch_one=True):
            raise ValueError(f"TELEFONE: O telefone '{telefone}' já existe no sistema vinculado a outro titular.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao validar telefone único: {e}")
        raise ValueError("Erro ao validar telefone no banco de dados.")
    return True

def validar_email_unico(email, processo_id=None, titular_id=None, titular_nome=None):
    if not email: return True
    
    # Verificar em processos (apresentante_email)
    query_proc = "SELECT id FROM processos WHERE apresentante_email = ?"
    params_proc = [email]
    if processo_id:
        query_proc += " AND id != ?"
        params_proc.append(processo_id)
    
    # Se o titular_nome for fornecido, ignoramos processos do mesmo titular
    if titular_nome:
        query_proc += " AND titular != ?"
        params_proc.append(titular_nome)
        
    try:
        if executar_query(query_proc, params_proc, fetch_one=True):
            raise ValueError(f"E-MAIL: O e-mail '{email}' já existe no sistema em outro processo de um titular diferente.")
            
        # Verificar em titulares
        query_tit = "SELECT id FROM titulares WHERE email = ?"
        params_tit = [email]
        
        # Se titular_nome for fornecido, tentamos achar o ID dele para ignorar na busca de duplicidade
        if titular_nome and not titular_id:
            tit_info = executar_query("SELECT id FROM titulares WHERE nome = ?", [titular_nome], fetch_one=True)
            if tit_info:
                titular_id = tit_info['id']

        # Se estamos editando um processo, precisamos encontrar se o titular vinculado a ele
        # é o mesmo que possui este e-mail, para não dar falso positivo.
        titular_vinculado_id = None
        if processo_id:
            try:
                proc = executar_query("SELECT titular FROM processos WHERE id = ?", [processo_id], fetch_one=True)
                if proc:
                    tit = executar_query("SELECT id FROM titulares WHERE nome = ?", [proc['titular']], fetch_one=True)
                    if tit:
                        titular_vinculado_id = tit['id']
            except Exception as e:
                logger.error(f"Erro ao buscar titular vinculado para validação de e-mail: {e}")

        target_titular_id = titular_id or titular_vinculado_id
        if target_titular_id:
            query_tit += " AND id != ?"
            params_tit.append(target_titular_id)
            
        if executar_query(query_tit, params_tit, fetch_one=True):
            raise ValueError(f"E-MAIL: O e-mail '{email}' já existe no sistema vinculado a outro titular.")
    except sqlite3.Error as e:
        logger.error(f"Erro ao validar e-mail único: {e}")
        raise ValueError("Erro ao validar e-mail no banco de dados.")
    return True

def validar_tipo_servico(tipo_id):
    if not isinstance(tipo_id, int) or tipo_id <= 0:
        raise ValueError("ID de tipo de serviço inválido.")
    result = executar_query("SELECT id FROM tipos_servico WHERE id = ? AND ativo = 1", [tipo_id], fetch_one=True)
    if not result:
        raise ValueError(f"Tipo de serviço com ID {tipo_id} inválido, não encontrado ou inativo.")
    return True

def validar_status(status_nome):
    if not status_nome:
        raise ValueError("Nome do status não pode ser vazio.")
    result = executar_query("SELECT id FROM status_processo WHERE nome = ? AND ativo = 1", [status_nome], fetch_one=True)
    if not result:
        raise ValueError(f"Status '{status_nome}' inválido, não encontrado ou inativo.")
    return True

def validar_nome_unico_db(tabela, coluna, nome, id_excluir=None):
    query = f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} = ?"
    params = [nome]
    if id_excluir:
        query += " AND id != ?"
        params.append(id_excluir)
    
    result = executar_query(query, params, fetch_one=True)
    if result['COUNT(*)'] > 0:
        raise ValueError(f"O nome '{nome}' já está em uso.")
    return True


# Reexportações de compatibilidade: a implementação vive em data.database.
from data.database import (
    get_sqlite_connection,
    executar_query,
    add_column_if_not_exists_sqlite,
)
from data.migrations import executar_migracoes_dados
from data.users import (
    verificar_tentativas_login, registrar_tentativa_login,
    get_user_by_username, update_user_last_login, create_user,
    create_password_reset_token, get_password_reset_token,
    mark_password_reset_token_as_used, gravar_auditoria_admin,
    gravar_tentativa_nao_autorizada,
)
from data.configuration import (
    get_config, set_config, obter_status_processo_config,
    get_email_config, save_email_config, send_email,
    get_backup_config, save_backup_config, update_last_backup_time,
)
from data.notifications import (
    criar_notificacao, listar_notificacoes_pendentes,
    marcar_notificacao_lida, marcar_todas_lidas, gerar_notificacoes_prazos,
    obter_preferencias_usuario, atualizar_preferencias_usuario,
    criar_notificacao_usuario, obter_notificacoes_usuario,
    marcar_notificacao_usuario_lida, obter_tema_usuario, salvar_tema_usuario,
)
from data.backup import (
    get_upload_folder, test_db_connection, optimize_database,
    check_and_repair_database, reconstruct_database, rebuild_fts_index,
    init_fts, _ensure_fts_triggers,
)

def init_db():
    """Inicializa o banco usando o módulo de schema, preservando a API legada."""
    from data.schema import init_db as initialize_schema
    return initialize_schema(
        criar_indices_performance=criar_indices_performance,
        init_fts=init_fts,
    )


def gravar_log(acao, processo_id=None, usuario_id=None, ip=None, descricao=None, contexto=None, connection=None):
    """
    Grava um log de atividade.
    - acao:      tipo da ação (ex: "Editou processo")
    - descricao: descrição principal — combinada com acao para exibição na tabela
                 (ex: "Processo: Titular (Matrícula: x)")
                 A coluna 'acao' no banco armazenará "Editou processo: Processo: Titular (Matrícula: x)"
    - contexto:  detalhes extras exibidos APENAS no modal de detalhe
                 (ex: "Status alterado de 'A' para 'B'\nCampo X: antigo → novo")
    Ações de segurança/acesso são gravadas em arquivo de texto.
    Ações de auditoria de processos são gravadas no banco de dados.
    """

    # Lista de ações de correspondência EXATA que devem ir para o arquivo de texto
    LOG_TO_FILE_ACTIONS = {
        'Logout do sistema', 'Link de recuperação de senha enviado',
        'Novo usuário registrado', 'Editou usuário', 'Inativou usuário',
        'Imprimiu lista de processos'
    }
    # Lista de PREFIXOS de ações que também devem ir para o arquivo de texto
    LOG_TO_FILE_PREFIXES = (
        'Login bem-sucedido',
        'Falha de login:',
        'Falha de cadastro:',
        'Erro durante login:',
        'Tentativa de login bloqueada',
        'Exportou'
    )

    # Ações que não devem ser registradas para evitar poluição
    ACOES_IGNORADAS = {
        'pesquisa_realizada', 'acquire_lock', 'renew_lock', 'release_lock',
        'acquire_lock_falha', 'renew_lock_falha', 'release_lock_falha'
    }

    if acao in ACOES_IGNORADAS:
        return  # Ignora o log silenciosamente

    # Prefixos permitidos para gravação no banco de dados.
    # Somente ações de Cadastro, Edição e Exclusão são registradas.
    PREFIXOS_BANCO = ('Cadastrou', 'Editou', 'Exclu')

    # Ações exatas adicionais que também devem ser gravadas no banco.
    ACOES_BANCO_EXATAS = {
        'Backup Manual',
        'Backup Automático',
        'Backup Automático SFTP',
        'Otimizou banco de dados',
        'Configurações de e-mail atualizadas',
    }

    log_para_arquivo = acao in LOG_TO_FILE_ACTIONS or acao.startswith(LOG_TO_FILE_PREFIXES)

    if log_para_arquivo:
        # Formata a mensagem para o arquivo de texto
        user_info = f"Usuário ID: {usuario_id if usuario_id else 'N/A'}"
        ip_info = f"IP: {ip if ip else 'N/A'}"
        detalhes = f"Detalhes: {descricao}" if descricao else f"Ação: {acao}"
        id_processo_info = f"Processo ID: {processo_id}" if processo_id else ""
        log_message = f"[{user_info}] [{ip_info}] - {detalhes} {id_processo_info}".strip()
        security_logger.info(log_message)

    elif acao.startswith(PREFIXOS_BANCO) or acao in ACOES_BANCO_EXATAS:
        # Somente ações de Cadastro, Edição e Exclusão são gravadas no banco.
        # 'acao' na tabela = "Tipo: Descrição principal" (formato original visível na listagem)
        # 'contexto' = detalhes extras exibidos apenas no modal
        final_acao = acao if descricao is None else f"{acao}: {descricao}"
        try:
            # Usa o usuario_id diretamente (passado pela sessão, sempre válido)
            safe_usuario_id = usuario_id

            # Valida processo_id
            safe_processo_id = None
            if processo_id is not None:
                try:
                    proc_exists = executar_query(
                        "SELECT 1 FROM processos WHERE id = ?", [processo_id], fetch_one=True
                    )
                    safe_processo_id = processo_id if proc_exists else None
                except Exception:
                    safe_processo_id = None

            executar_query(
                "INSERT INTO logs (acao, contexto, processo_id, usuario_id, ip, timestamp) "
                "VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))",
                [final_acao, contexto, safe_processo_id, safe_usuario_id, ip],
                connection=connection
            )
        except Exception as e:
            logger.error(f"Falha ao gravar log no BANCO DE DADOS para ação '{final_acao}': {e}", exc_info=True)









def obter_tipos_servico():
    return executar_query("SELECT id, nome, descricao, ativo, prazo_padrao FROM tipos_servico ORDER BY nome ASC")


def get_status_id_by_name(status_name):
    result = executar_query("SELECT id FROM status_processo WHERE nome = ?", [status_name], fetch_one=True)
    return result['id'] if result else None

def obter_usuarios_para_selecao():
    return executar_query("SELECT id, nome FROM usuarios WHERE ativo = 1 ORDER BY nome ASC")

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

def update_processo(processo_id, titular, titular_telefone, titular_email, matricula, tipo_id, data_entrada, status_id, prazo_final, apresentante, apresentante_telefone, apresentante_email, responsavel_id, envolvido_notas, observacoes, data_conclusao, possui_matricula=0, connection=None, titular_id=None, apresentante_id=None):
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
            P.id, P.numero_processo, P.titular, P.matricula,
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
    if filtros.get('busca'):
        busca_termo = f"%{filtros['busca']}%"
        # A busca já contempla P.matricula LIKE ?, então a funcionalidade de pesquisar pelo número da matrícula já está presente na lógica de busca global.
        where_clauses.append("(P.numero_processo LIKE ? OR P.titular LIKE ? OR P.matricula LIKE ? OR U.nome LIKE ? OR TS.nome LIKE ? OR SP.nome LIKE ?)")
        query_params.extend([busca_termo, busca_termo, busca_termo, busca_termo, busca_termo, busca_termo])
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
    
    for r in results:
        if isinstance(r['prazo_final'], str) and len(r['prazo_final']) >= 10:
            r['prazo_final_dt'] = datetime.strptime(r['prazo_final'].split(' ')[0], '%Y-%m-%d').date()
        else:
            r['prazo_final_dt'] = None
    return results


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

def acquire_lock(table_name, record_id, user_id, timeout_minutes):
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        
        now_dt = datetime.now()
        cursor.execute("DELETE FROM record_locks WHERE expires_at < ?", [now_dt.strftime('%Y-%m-%d %H:%M:%S')])
        logger.debug(f"Locks expirados para {table_name}:{record_id} limpos.")

        cursor.execute("SELECT user_id, locked_at, expires_at FROM record_locks WHERE table_name = ? AND record_id = ?",
                       [table_name, record_id])
        existing_lock = cursor.fetchone()

        if existing_lock:
            locked_by_user_id = existing_lock['user_id']
            expires_at_str = existing_lock['expires_at']
            expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')

            if locked_by_user_id == user_id:
                new_expires_at = now_dt + timedelta(minutes=timeout_minutes)
                cursor.execute("UPDATE record_locks SET expires_at = ?, locked_at = ? WHERE table_name = ? AND record_id = ?",
                               [new_expires_at.strftime('%Y-%m-%d %H:%M:%S'), now_dt.strftime('%Y-%m-%d %H:%M:%S'), table_name, record_id])
                logger.info(f"Lock para {table_name}:{record_id} renovado por usuário {user_id}. Expira em: {new_expires_at}")
                return True
            elif now_dt < expires_at:
                user_info = executar_query("SELECT nome FROM usuarios WHERE id = ?", [locked_by_user_id], fetch_one=True, connection=conn)
                locked_by_name = user_info['nome'] if user_info else f"Usuário (ID {locked_by_user_id})"
                logger.warning(f"Tentativa de adquirir lock em {table_name}:{record_id} por {user_id}. Já bloqueado por {locked_by_name} até {expires_at}.")
                return {'error': f"Este registro está sendo editado por {locked_by_name}. Tente novamente mais tarde (expira em {expires_at.strftime('%H:%M:%S')}).", 'type': 'warning', 'code': 409}
            else:
                cursor.execute("DELETE FROM record_locks WHERE table_name = ? AND record_id = ?", [table_name, record_id])
                logger.info(f"Lock expirado para {table_name}:{record_id} por usuário {locked_by_user_id} removido. Tentando adquirir novo lock.")
        
        # Correção da sintaxe aqui: minutes=timeout_minutes
        new_expires_at = now_dt + timedelta(minutes=timeout_minutes)
        try:
            cursor.execute("INSERT INTO record_locks (table_name, record_id, user_id, locked_at, expires_at) VALUES (?, ?, ?, ?, ?)",
                           [table_name, record_id, user_id, now_dt.strftime('%Y-%m-%d %H:%M:%S'), new_expires_at.strftime('%Y-%m-%d %H:%M:%S')])
            logger.info(f"Lock em {table_name}:{record_id} adquirido por usuário {user_id}. Expira em: {new_expires_at}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Falha de integridade ao adquirir lock para {table_name}:{record_id} por {user_id}. Conflito de concorrência. Retrying acquire_lock...")
            return acquire_lock(table_name, record_id, user_id, timeout_minutes)
        except Exception as e:
            logger.error(f"Erro inesperado ao adquirir lock para {table_name}:{record_id} por {user_id}: {e}", exc_info=True)
            return {'error': 'Erro interno ao tentar bloquear o registro.', 'type': 'danger', 'code': 500}

# --- INÍCIO DA CORREÇÃO DE FLUXO DE TRABALHO DE RECUPERAÇÃO DE SENHA ---

def release_lock(table_name, record_id, user_id):
    """
    Liberta um bloqueio de registo específico para um utilizador.
    """
    try:
        with get_sqlite_connection() as conn:
            cursor = conn.cursor()
            
            # ESTA É A LINHA CRÍTICA CORRIGIDA:
            # Apaga o bloqueio para a tabela e registo específicos que pertencem ao utilizador atual.
            cursor.execute(
                "DELETE FROM record_locks WHERE table_name = ? AND record_id = ? AND user_id = ?",
                [table_name, record_id, user_id]
            )
            
            rows_affected = cursor.rowcount
            
            if rows_affected > 0:
                logger.info(f"Lock para {table_name}:{record_id} libertado com sucesso pelo utilizador {user_id}.")
                return {'success': True}
            else:
                # Log informativo de que o bloqueio não foi encontrado, pois provavelmente já havia sido liberado.
                logger.info(f"Lock de {table_name}:{record_id} não encontrado - já expirado ou liberado.")
                return {'success': False, 'message': 'O bloqueio não foi encontrado para ser libertado.'}

    except Exception as e:
        logger.error(f"Erro inesperado ao libertar lock para {table_name}:{record_id}: {e}", exc_info=True)
        return {'success': False, 'error': 'Erro interno do servidor ao tentar libertar o bloqueio.'}

def renew_lock(table_name, record_id, user_id, timeout_minutes):
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        
        now_dt = datetime.now()
        new_expires_at = now_dt + timedelta(minutes=timeout_minutes)
        
        cursor.execute("UPDATE record_locks SET expires_at = ?, locked_at = ? WHERE table_name = ? AND record_id = ? AND user_id = ? AND expires_at > ?",
                       [new_expires_at.strftime('%Y-%m-%d %H:%M:%S'), now_dt.strftime('%Y-%m-%d %H:%M:%S'), table_name, record_id, user_id, now_dt.strftime('%Y-%m-%d %H:%M:%S')])
        rows_affected = cursor.rowcount
        
        if rows_affected > 0:
            logger.debug(f"Lock para {table_name}:{record_id} renovado com sucesso por usuário {user_id}.")
            return {'success': True}
        else:
            logger.warning(f"Falha ao renovar lock para {table_name}:{record_id} por {user_id}. Tentando readquirir...")
            return acquire_lock(table_name, record_id, user_id, timeout_minutes)
            
def release_all_locks(user_id):
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM record_locks WHERE user_id = ?", [user_id])
        rows_affected = cursor.rowcount
        if rows_affected > 0:
            logger.info(f"{rows_affected} locks liberados para o usuário {user_id}.")
        return {'success': True, 'count': rows_affected}

def add_status_processo(nome, hex_color):
    validar_nome_unico_db('status_processo', 'nome', nome)
    return executar_query(
        "INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)",
        [nome, hex_color, 1]
    )

def update_status_processo(status_id, nome, hex_color, ativo):
    current_status = executar_query("SELECT nome, ativo FROM status_processo WHERE id = ?", [status_id], fetch_one=True)
    if not current_status:
        raise ValueError("Status não encontrado para edição.")

    validar_nome_unico_db('status_processo', 'nome', nome, status_id)
        
    return executar_query(
        "UPDATE status_processo SET nome = ?, hex_color = ?, ativo = ? WHERE id = ?",
        [nome, hex_color, 1 if ativo else 0, status_id]
    )

def toggle_status_processo(status_id):
    current_status = executar_query("SELECT nome, ativo FROM status_processo WHERE id = ?", [status_id], fetch_one=True)
    if not current_status:
        raise ValueError("Status não encontrado.")
    
    novo_status = not current_status['ativo']
    
    if current_status['ativo'] == 1 and not novo_status:
        count_in_use = executar_query("SELECT COUNT(*) FROM processos WHERE status_id = ?", [status_id], fetch_one=True)['COUNT(*)']
        if count_in_use > 0:
            raise ValueError(f"Não foi possível desativar o status '{current_status['nome']}' porque ele está sendo utilizado por {count_in_use} processo(s).")

    return executar_query(
        "UPDATE status_processo SET ativo = ? WHERE id = ?",
        [1 if novo_status else 0, status_id]
    )

def add_tipo_servico(nome, descricao, prazo_padrao):
    if prazo_padrao is None or prazo_padrao < 0:
        prazo_padrao = 30
    validar_nome_unico_db('tipos_servico', 'nome', nome)
    return executar_query(
        "INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)",
        [nome, descricao, 1, prazo_padrao]
    )

def update_tipo_servico(service_id, nome, descricao, ativo, prazo_padrao):
    current_service = executar_query("SELECT nome, ativo FROM tipos_servico WHERE id = ?", [service_id], fetch_one=True)
    if not current_service:
        raise ValueError("Tipo de serviço não encontrado para edição.")

    if prazo_padrao is None or prazo_padrao < 0:
        prazo_padrao = 30
    validar_nome_unico_db('tipos_servico', 'nome', nome, service_id)

    return executar_query(
        "UPDATE tipos_servico SET nome = ?, descricao = ?, ativo = ?, prazo_padrao = ? WHERE id = ?",
        [nome, descricao, 1 if ativo else 0, prazo_padrao, service_id]
    )

def toggle_tipo_servico(service_id):
    current_service = executar_query("SELECT nome, ativo FROM tipos_servico WHERE id = ?", [service_id], fetch_one=True)
    if not current_service:
        raise ValueError("Tipo de serviço não encontrado.")

    novo_status = not current_service['ativo']

    if current_service['ativo'] == 1 and not novo_status:
        count_in_use = executar_query("SELECT COUNT(*) FROM processos WHERE tipo_id = ?", [service_id], fetch_one=True)['COUNT(*)']
        if count_in_use > 0:
            raise ValueError(f"Não foi possível desativar o serviço '{current_service['nome']}' porque ele está sendo utilizado por {count_in_use} processo(s).")
            
    return executar_query(
        "UPDATE tipos_servico SET ativo = ? WHERE id = ?",
        [1 if novo_status else 0, service_id]
    )












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

def get_empresa_info():
    return executar_query("""
        SELECT id, cartorio, oficial, substituta, endereco,
               telefone, email, logo,
               criado_em, atualizado_em
        FROM empresa LIMIT 1""", fetch_one=True)

def save_empresa_info(data, is_new_record=False, connection=None):
    if data.get('email') and not validar_email(data['email']):
        raise ValueError("E-mail da empresa inválido.")

    if data.get('telefone') and not validar_telefone(data['telefone']):
        raise ValueError("Telefone da empresa inválido.")

    field_mapping = {
        'cartorio': 'cartorio',
        'oficial': 'oficial',
        'substituta': 'substituta',
        'endereco': 'endereco',
        'telefone': 'telefone',
        'email': 'email',
        'logo': 'logo'
    }
    
    filtered_data = {}
    for k, v in data.items():
        if k in field_mapping:
            filtered_data[field_mapping[k]] = v

    if is_new_record:
        if 'logo' in filtered_data and not filtered_data['logo']:
            del filtered_data['logo']
        
        columns = ', '.join(filtered_data.keys())
        placeholders = ', '.join(['?'] * len(filtered_data))
        query = f"INSERT INTO empresa ({columns}, criado_em, atualizado_em) VALUES ({placeholders}, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))"
        return executar_query(query, list(filtered_data.values()), connection=connection)
    else:
        update_fields = []
        update_params = []
        for k_lower, v in filtered_data.items():
            if k_lower == 'logo':
                if v is None or v == '':
                    update_fields.append(f"{k_lower} = NULL")
                else:
                    update_fields.append(f"{k_lower} = ?")
                    update_params.append(v)
            else:
                update_fields.append(f"{k_lower} = ?")
                update_params.append(v)
        
        query = f"UPDATE empresa SET {', '.join(update_fields)}, atualizado_em = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?"
        update_params.append(data['id'])
        
        return executar_query(query, update_params, connection=connection)







def is_record_locked(table_name, record_id, current_user_id):
    """
    Verifica se um registro está bloqueado por OUTRO usuário.
    Retorna os dados do bloqueio se estiver bloqueado, caso contrário, retorna None.
    """
    from datetime import datetime
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Primeiro, limpa locks expirados para garantir que a verificação seja precisa.
    try:
        executar_query("DELETE FROM record_locks WHERE expires_at < ?", [now_str])
    except Exception as e:
        logger.error(f"Falha ao limpar locks expirados antes da verificação: {e}")

    # Agora, verifica se existe um lock ativo para o registro que não pertence ao usuário atual.
    lock_info = executar_query(
        """
        SELECT L.user_id, U.nome as user_nome
        FROM record_locks L
        JOIN usuarios U ON L.user_id = U.id
        WHERE L.table_name = ? AND L.record_id = ? AND L.user_id != ?
        """,
        [table_name, record_id, current_user_id],
        fetch_one=True
    )
    
    return lock_info if lock_info else None

# --- Funções para Titulares ---

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
    
    colunas_validas = {'nome': 't.nome', 'email': 't.email', 'telefone': 't.telefone', 'processos': 'total_processos'}
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


# ============================================
# FUNÇÕES DE PERFORMANCE E ÍNDICES - v3.2.3+
# ============================================

def criar_indices_performance(cursor):
    """Cria índices otimizados para melhorar performance das queries."""
    try:
        indices = [
            # Processos
            "CREATE INDEX IF NOT EXISTS idx_processos_status ON processos(status_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_tipo ON processos(tipo_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_responsavel ON processos(responsavel_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_created_at ON processos(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_processos_numero ON processos(numero_processo)",
            "CREATE INDEX IF NOT EXISTS idx_processos_matricula ON processos(matricula)",
            "CREATE INDEX IF NOT EXISTS idx_processos_prazo ON processos(prazo_final, data_conclusao)",
            
            # Anexos
            "CREATE INDEX IF NOT EXISTS idx_anexos_processo_id ON anexos_processos(processo_id)",
            
            # Histórico (coluna correta: timestamp_alteracao)
            "CREATE INDEX IF NOT EXISTS idx_historico_processo ON historico_processos(processo_id, timestamp_alteracao DESC)",
            "CREATE INDEX IF NOT EXISTS idx_historico_usuario ON historico_processos(usuario_id, timestamp_alteracao DESC)",
            
            # Titulares (removido índice cpf_cnpj pois a coluna não existe na tabela)
            "CREATE INDEX IF NOT EXISTS idx_titulares_nome ON titulares(nome)",
            
            # Usuários
            "CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_ativos ON usuarios(ativo)",
            
            # Logs
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs(usuario_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_logs_acao ON logs(acao, timestamp DESC)",
            
            # Login attempts
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip, tempo DESC)",
            
            # Notificações
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario ON notificacoes(usuario_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_lida ON notificacoes(usuario_id, lida)",
            
            # Permissões (v3.3.5)
            "CREATE INDEX IF NOT EXISTS idx_permissoes_usuario ON permissoes_usuarios(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_permissoes_modulo ON permissoes_usuarios(modulo_id)",
            "CREATE INDEX IF NOT EXISTS idx_permissoes_usuario_modulo ON permissoes_usuarios(usuario_id, modulo_id)",
            
            # Módulos Sistema (v3.3.5)
            "CREATE INDEX IF NOT EXISTS idx_modulos_categoria ON modulos_sistema(categoria, ordem)",
            "CREATE INDEX IF NOT EXISTS idx_modulos_ativo ON modulos_sistema(ativo)",

            # Perfis de Permissão
            "CREATE INDEX IF NOT EXISTS idx_perfis_permissao_nome ON perfis_permissao(nome)",
            "CREATE INDEX IF NOT EXISTS idx_perfis_modulos_perfil ON perfis_permissao_modulos(perfil_id)",
            "CREATE INDEX IF NOT EXISTS idx_usuario_perfil_usuario ON usuario_perfil(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_usuario_perfil_perfil ON usuario_perfil(perfil_id)",

            # Auditoria e Segurança (v3.16.5)
            "CREATE INDEX IF NOT EXISTS idx_auditoria_admin_id ON auditoria_admin(admin_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_afetado ON auditoria_admin(usuario_afetado_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auditoria_acao ON auditoria_admin(acao, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tentativas_usuario ON tentativas_acesso_nao_autorizado(usuario_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tentativas_ip ON tentativas_acesso_nao_autorizado(ip, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario_lida ON notificacoes_usuario(usuario_id, lida)",
        ]
        
        for index_sql in indices:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Índice já existe ou erro ao criar: {e}")
        
        logger.info("Índices de performance criados/verificados com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao criar índices: {e}", exc_info=True)


# ============================================
# FUNÇÕES DE BUSCA FULL-TEXT (FTS5) - v3.2.3+
# ============================================







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


# ============================================
# FUNÇÕES DE TEMPLATES DE PROCESSOS - v3.2.3+
# ============================================

def criar_template(nome, descricao, tipo_id, status_id, prazo_dias, 
                   observacoes_padrao, usuario_id, publico=0):
    """Cria um novo template de processo."""
    query = """
        INSERT INTO templates_processos 
        (nome, descricao, tipo_id, status_id, prazo_dias, observacoes_padrao, usuario_criador, publico)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    return executar_query(query, [nome, descricao, tipo_id, status_id, 
                                  prazo_dias, observacoes_padrao, usuario_id, publico])


def listar_templates(usuario_id=None):
    """Lista templates disponíveis para o usuário."""
    if usuario_id:
        query = """
            SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome, s.hex_color as status_cor
            FROM templates_processos t
            LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
            LEFT JOIN status_processo s ON t.status_id = s.id
            WHERE t.publico = 1 OR t.usuario_criador = ?
            ORDER BY t.nome
        """
        return executar_query(query, [usuario_id], fetch_all=True) or []
    else:
        query = """
            SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome, s.hex_color as status_cor
            FROM templates_processos t
            LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
            LEFT JOIN status_processo s ON t.status_id = s.id
            WHERE t.publico = 1
            ORDER BY t.nome
        """
        return executar_query(query, fetch_all=True) or []


def obter_template(template_id):
    """Obtém um template específico."""
    query = """
        SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome
        FROM templates_processos t
        LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
        LEFT JOIN status_processo s ON t.status_id = s.id
        WHERE t.id = ?
    """
    return executar_query(query, [template_id], fetch_one=True)


def atualizar_template(template_id, dados):
    """Atualiza um template existente."""
    campos = []
    valores = []
    
    campos_permitidos = ['nome', 'descricao', 'tipo_id', 'status_id', 
                        'prazo_dias', 'observacoes_padrao', 'publico']
    
    for campo in campos_permitidos:
        if campo in dados:
            campos.append(f"{campo} = ?")
            valores.append(dados[campo])
    
    if not campos:
        return False
    
    campos.append("updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
    valores.append(template_id)
    
    query = f"UPDATE templates_processos SET {', '.join(campos)} WHERE id = ?"
    return executar_query(query, valores)


def excluir_template(template_id, usuario_id):
    """Exclui um template (apenas o criador pode excluir)."""
    query = "DELETE FROM templates_processos WHERE id = ? AND usuario_criador = ?"
    return executar_query(query, [template_id, usuario_id])


# ============================================
# FUNÇÕES DE NOTIFICAÇÕES - v3.2.3+
# ============================================











# ============================================
# FUNÇÕES DE PREFERÊNCIAS DO USUÁRIO - v3.2.3+
# ============================================





# ============================================
# FUNÇÕES DE AUDITORIA E SEGURANÇA - v3.3.3+
# ============================================











def gerar_senha_temporaria(tamanho=12):
    """
    Gera uma senha temporária forte.
    
    Args:
        tamanho: Tamanho da senha (padrão 12)
    
    Returns:
        Senha temporária gerada
    """
    import string
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(tamanho))


def mascarar_email(email):
    """
    Mascara um email para exibição segura.
    
    Args:
        email: Email a ser mascarado
    
    Returns:
        Email mascarado (exemplo: m***@email.com)
    """
    if not email or '@' not in email:
        return email
    
    partes = email.split('@')
    usuario = partes[0]
    dominio = partes[1]
    
    if len(usuario) <= 2:
        usuario_mascarado = usuario[0] + '*'
    else:
        usuario_mascarado = usuario[0] + '***'
    
    return f"{usuario_mascarado}@{dominio}"


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


def listar_apresentantes(filtros=None, pagina=1, registros_por_pagina=10):
    """Lista apresentantes com paginação e filtros."""
    import math
    offset = (pagina - 1) * registros_por_pagina
    
    query = """SELECT r.*,
               (SELECT COUNT(*) FROM processos pr
                  WHERE pr.apresentante_id = r.id
                     OR (pr.apresentante_id IS NULL AND pr.apresentante = r.nome)) as total_processos
               FROM apresentantes r WHERE 1=1"""
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
    
    colunas_validas = {'nome': 'r.nome', 'email': 'r.email', 'telefone': 'r.telefone', 'processos': 'total_processos'}
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
               (SELECT COUNT(*) FROM processos pr
                  WHERE pr.apresentante_id = r.id
                     OR (pr.apresentante_id IS NULL AND pr.apresentante = r.nome)) as total_processos
               FROM apresentantes r WHERE r.id = ?"""
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
