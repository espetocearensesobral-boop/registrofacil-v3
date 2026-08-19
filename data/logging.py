"""Emissão compatível de eventos operacionais, de segurança e de auditoria."""

from __future__ import annotations

import logging
import re

from data.database import executar_query
from utils.log_events import emit_event, event_extra, new_event_id, sanitize_details, sanitize_text
from utils.logger import (
    auth_logger,
    manutencao_logger,
    operacional_logger,
    security_logger,
    sistema_logger,
)

LOG_TO_FILE_ACTIONS = {
    'Logout do sistema',
    'Link de recuperação de senha enviado',
    'Novo usuário registrado',
    'Editou usuário',
    'Inativou usuário',
    'Imprimiu lista de processos',
}
LOG_TO_FILE_PREFIXES = (
    'Login bem-sucedido',
    'Falha de login:',
    'Falha de cadastro:',
    'Erro durante login:',
    'Tentativa de login bloqueada',
    'Exportou',
)

# Ações muito frequentes continuam fora da auditoria persistente, mas falhas
# deixam de ser silenciosas e aparecem em nível warning.
IGNORED_ACTIONS = {
    'pesquisa_realizada',
    'acquire_lock',
    'renew_lock',
    'release_lock',
}
LOCK_FAILURE_ACTIONS = {
    'acquire_lock_falha',
    'renew_lock_falha',
    'release_lock_falha',
}
DB_EXACT_ACTIONS = {
    'Backup Manual',
    'Backup Automático',
    'Backup Automático SFTP',
    'Otimizou banco de dados',
    'Configurações de e-mail atualizadas',
}
DB_PREFIXES = ('Cadastrou', 'Editou', 'Exclu', 'Criou', 'Inativou', 'Ativou', 'Restaur', 'Reconstruiu', 'Reparou')


def _event_type(action: str) -> str:
    normalized = re.sub(r'[^a-z0-9]+', '.', action.lower(), flags=re.UNICODE).strip('.')
    return normalized[:120] or 'generic'


def _domain_for(action: str, explicit: str | None = None) -> str:
    if explicit in {'auth', 'operacional', 'sistema', 'manutencao'}:
        return explicit
    if action.startswith(('Login', 'Falha de login', 'Tentativa de login', 'Logout', 'Link de recuperação', 'Redefinição', 'Falha de cadastro')):
        return 'auth'
    if action.startswith(('Backup', 'Restaur', 'Otimizou banco', 'Reconstruiu', 'Reparou')):
        return 'manutencao'
    if action.startswith(('Erro no banco', 'Migração', 'FTS', 'Configuração do sistema')):
        return 'sistema'
    return 'operacional'


def _logger_for(domain: str):
    return {
        'auth': auth_logger,
        'manutencao': manutencao_logger,
        'sistema': sistema_logger,
        'operacional': operacional_logger,
    }.get(domain, operacional_logger)


def _level_for(action: str) -> int:
    if action in LOCK_FAILURE_ACTIONS or action.lower().startswith(('falha', 'erro', 'não autorizado')):
        return logging.WARNING
    if action.lower().startswith(('exclu', 'inativou', 'reparou', 'reconstruiu')):
        return logging.INFO
    return logging.INFO


def gravar_log(
    acao,
    processo_id=None,
    usuario_id=None,
    ip=None,
    descricao=None,
    contexto=None,
    connection=None,
    *,
    event_id=None,
    request_id=None,
    domain=None,
    event_type=None,
    severity=None,
):
    """Emite um evento e, quando aplicável, grava a auditoria operacional.

    Os parâmetros originais continuam compatíveis. Os argumentos nomeados
    adicionais permitem que novas rotas forneçam classificação explícita.
    """
    action = sanitize_text(acao, 160) or 'evento_sem_acao'
    description = sanitize_text(descricao)
    safe_context = sanitize_details(contexto)
    resolved_domain = _domain_for(action, domain)
    resolved_event_type = event_type or _event_type(action)
    resolved_event_id = event_id or new_event_id()
    level = getattr(logging, (severity or '').upper(), _level_for(action)) if isinstance(severity, str) else _level_for(action)
    extras = event_extra(
        event_id=resolved_event_id,
        domain=resolved_domain,
        event_type=resolved_event_type,
        entity_id=processo_id,
        user_id=usuario_id,
        ip=ip,
        request_id_value=request_id,
        details=safe_context or description,
    )

    if action in IGNORED_ACTIONS:
        return resolved_event_id

    target_logger = _logger_for(resolved_domain)
    message = action if not description else f'{action}: {description}'
    target_logger.log(level, sanitize_text(message), extra=extras)

    if (action in LOG_TO_FILE_ACTIONS or action.startswith(LOG_TO_FILE_PREFIXES)) and security_logger is not target_logger:
        security_logger.log(level, sanitize_text(message), extra=extras)

    should_store = action in DB_EXACT_ACTIONS or action.startswith(DB_PREFIXES)
    if not should_store:
        return resolved_event_id

    safe_process_id = None
    if processo_id is not None:
        try:
            if connection is not None:
                safe_process_id = processo_id
            else:
                exists = executar_query('SELECT 1 FROM processos WHERE id = ?', [processo_id], fetch_one=True)
                safe_process_id = processo_id if exists else None
        except Exception:
            safe_process_id = None

    try:
        final_action = action if description is None else f'{action}: {description}'
        executar_query(
            """
            INSERT INTO logs (
                acao, contexto, processo_id, usuario_id, ip,
                event_id, request_id, domain, event_type, entity_id, severity, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            """,
            [
                final_action,
                safe_context,
                safe_process_id,
                usuario_id,
                sanitize_text(ip, 128) if ip else None,
                resolved_event_id,
                extras['request_id'],
                resolved_domain,
                resolved_event_type,
                str(safe_process_id) if safe_process_id is not None else None,
                logging.getLevelName(level),
            ],
            connection=connection,
        )
    except Exception as exc:
        # A falha da auditoria nunca deve esconder a operação original, mas
        # precisa ficar registrada com o mesmo event_id para diagnóstico.
        operacional_logger.error(
            f'Falha ao persistir evento de auditoria {resolved_event_id}: {exc}',
            extra=event_extra(
                event_id=resolved_event_id,
                domain='sistema',
                event_type='audit.persistence_failed',
                entity_id=processo_id,
                user_id=usuario_id,
                ip=ip,
                request_id_value=request_id,
                details={'action': action, 'error': str(exc)},
            ),
            exc_info=True,
        )
    return resolved_event_id
