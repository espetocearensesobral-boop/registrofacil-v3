from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from data.database import executar_query
from utils.log_events import event_extra, new_event_id, remember_event_id, sanitize_details, sanitize_text
from utils.logger import (
    auth_logger,
    manutencao_logger,
    operacional_logger,
    security_logger,
    sistema_logger,
)


@dataclass(frozen=True)
class EventPolicy:
    """Política única para classificação, persistência e espelhamento do evento."""

    event_type: str
    domain: str
    persist: bool = True
    mirror_auth: bool = False
    action_names: tuple[str, ...] = ()
    action_prefixes: tuple[str, ...] = ()


EVENT_CATALOG = (
    EventPolicy(
        event_type='auth.login.success',
        domain='auth',
        action_prefixes=('Login bem-sucedido',),
    ),
    EventPolicy(
        event_type='auth.login.failed',
        domain='auth',
        action_prefixes=('Falha de login:',),
    ),
    EventPolicy(
        event_type='auth.login.blocked',
        domain='auth',
        action_prefixes=('Tentativa de login bloqueada',),
    ),
    EventPolicy(
        event_type='auth.login.error',
        domain='auth',
        action_prefixes=('Erro durante login:',),
    ),
    EventPolicy(
        event_type='auth.registration.failed',
        domain='auth',
        action_prefixes=('Falha de cadastro:',),
    ),
    EventPolicy(
        event_type='auth.logout',
        domain='auth',
        action_names=('Logout do sistema',),
    ),
    EventPolicy(
        event_type='auth.password_reset.sent',
        domain='auth',
        action_names=('Link de recuperação de senha enviado',),
    ),
    EventPolicy(
        event_type='auth.password_reset.completed',
        domain='auth',
        action_names=('Redefinição de Senha',),
    ),
    EventPolicy(
        event_type='maintenance.backup',
        domain='manutencao',
        action_prefixes=('Backup',),
    ),
    EventPolicy(
        event_type='maintenance.backup.restore',
        domain='manutencao',
        action_names=('Restauração de backup',),
    ),
    EventPolicy(
        event_type='maintenance.database.optimize',
        domain='manutencao',
        action_names=('Otimizou banco de dados',),
    ),
    EventPolicy(
        event_type='maintenance.database.rebuild',
        domain='manutencao',
        action_prefixes=('Reconstruiu banco',),
    ),
    EventPolicy(
        event_type='maintenance.database.repair',
        domain='manutencao',
        action_prefixes=('Reparou banco',),
    ),
    EventPolicy(
        event_type='maintenance.fts.rebuild',
        domain='manutencao',
        action_names=('Reconstruiu índice FTS5',),
    ),
    EventPolicy(
        event_type='operational.export',
        domain='operacional',
        mirror_auth=True,
        action_prefixes=('Exportou',),
    ),
    EventPolicy(
        event_type='operational.process.list_printed',
        domain='operacional',
        mirror_auth=True,
        action_names=('Imprimiu lista de processos',),
    ),
    EventPolicy(
        event_type='operational.user.updated',
        domain='operacional',
        mirror_auth=True,
        action_names=('Editou usuário',),
    ),
    EventPolicy(
        event_type='operational.user.deactivated',
        domain='operacional',
        mirror_auth=True,
        action_names=('Inativou usuário',),
    ),
)

# Eventos deliberadamente de alta frequência; falhas de lock permanecem auditáveis.
IGNORED_ACTIONS = frozenset({
    'pesquisa_realizada',
    'pesquisa_inteligente_realizada',
    'acquire_lock',
    'renew_lock',
    'release_lock',
})
LOCK_FAILURE_ACTIONS = frozenset({
    'acquire_lock_falha',
    'renew_lock_falha',
    'release_lock_falha',
})


def _event_type(action: str) -> str:
    normalized = unicodedata.normalize('NFKD', action)
    normalized = normalized.encode('ascii', 'ignore').decode('ascii')
    normalized = re.sub(r'[^a-z0-9]+', '.', normalized.lower()).strip('.')
    return normalized[:120] or 'generic'


def _policy_for(action: str, explicit_domain: str | None, explicit_event_type: str | None) -> EventPolicy:
    for policy in EVENT_CATALOG:
        if action in policy.action_names or any(action.startswith(prefix) for prefix in policy.action_prefixes):
            return EventPolicy(
                event_type=explicit_event_type or policy.event_type,
                domain=explicit_domain or policy.domain,
                persist=policy.persist,
                mirror_auth=policy.mirror_auth,
            )
    return EventPolicy(
        event_type=explicit_event_type or _event_type(action),
        domain=explicit_domain if explicit_domain in {'auth', 'operacional', 'sistema', 'manutencao'} else 'operacional',
        persist=True,
    )


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
    """Emite e persiste um evento segundo o catálogo central de políticas."""
    action = sanitize_text(acao, 160) or 'evento_sem_acao'
    description = sanitize_text(descricao)
    safe_context = sanitize_details(contexto)
    policy = _policy_for(action, domain, event_type)
    resolved_event_id = event_id or new_event_id()
    remember_event_id(resolved_event_id)
    level = (
        getattr(logging, severity.upper(), _level_for(action))
        if isinstance(severity, str) else _level_for(action)
    )
    extras = event_extra(
        event_id=resolved_event_id,
        domain=policy.domain,
        event_type=policy.event_type,
        entity_id=processo_id,
        user_id=usuario_id,
        ip=ip,
        request_id_value=request_id,
        details=safe_context or description,
    )

    if action in IGNORED_ACTIONS:
        return resolved_event_id

    target_logger = _logger_for(policy.domain)
    message = action if not description else f'{action}: {description}'
    target_logger.log(level, sanitize_text(message), extra=extras)

    if policy.mirror_auth and security_logger is not target_logger:
        security_logger.log(level, sanitize_text(message), extra=extras)

    if not policy.persist:
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
        event_details = safe_context or description
        executar_query(
            """
            INSERT INTO logs (
                acao, contexto, processo_id, usuario_id, ip,
                event_id, request_id, domain, event_type, entity_id, severity, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            """,
            [
                action,
                event_details,
                safe_process_id,
                usuario_id,
                sanitize_text(ip, 128) if ip else None,
                resolved_event_id,
                extras['request_id'],
                policy.domain,
                policy.event_type,
                str(safe_process_id) if safe_process_id is not None else None,
                logging.getLevelName(level),
            ],
            connection=connection,
        )
    except Exception as exc:
        # A falha da auditoria operacional não deve esconder a operação original.
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
