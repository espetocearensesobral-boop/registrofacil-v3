"""Validações de dados de processos e cadastros."""

import re
import sqlite3

from data.database import executar_query
from utils.logger import logger

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

