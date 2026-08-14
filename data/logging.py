"""Registro de logs de segurança e auditoria."""

from data.database import executar_query
from utils.logger import logger, security_logger

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

