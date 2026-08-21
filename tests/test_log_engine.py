import logging
import sqlite3

import pytest

from data import database
from data.audit_logs import obter_logs_seguranca
from utils.log_events import event_extra, sanitize_text
from utils.logger_config import RequestContextFilter, SizeAndTimeRotatingFileHandler


def test_log_event_sanitizes_secrets_and_has_correlation():
    assert 'supersecret' not in sanitize_text('senha=supersecret')
    extras = event_extra(domain='auth', event_type='login.failed', user_id=7, ip='192.0.2.10')
    assert len(extras['event_id']) == 20
    assert extras['domain'] == 'auth'
    assert extras['event_type'] == 'login.failed'
    assert extras['user_id'] == '7'


def test_size_rotating_handler_creates_rotated_file(tmp_path):
    path = tmp_path / 'operacional.log'
    test_logger = logging.getLogger('registrofacil.test_rotation')
    test_logger.handlers.clear()
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False
    handler = SizeAndTimeRotatingFileHandler(
        str(path), when='midnight', interval=1, backupCount=0, max_bytes=220
    )
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(logging.Formatter('%(event_id)s %(message)s'))
    test_logger.addHandler(handler)
    try:
        for index in range(20):
            test_logger.info('x' * 40, extra=event_extra(domain='operacional', event_type='test', entity_id=index))
        handler.flush()
        assert path.exists()
        assert any(item.name.startswith('operacional.log.') for item in tmp_path.iterdir())
    finally:
        test_logger.removeHandler(handler)
        handler.close()


def test_schema_contains_structured_log_columns(temp_database):
    with sqlite3.connect(str(temp_database)) as conn:
        for table, expected in {
            'logs': {'event_id', 'request_id', 'domain', 'event_type', 'entity_id', 'severity'},
            'auditoria_admin': {'event_id', 'request_id'},
            'tentativas_acesso_nao_autorizado': {'event_id', 'request_id'},
            'login_attempts': {'event_id'},
        }.items():
            columns = {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
            assert expected <= columns


def test_security_query_returns_stable_empty_contract(temp_database):
    result = obter_logs_seguranca({}, pagina=1, por_pagina=50)
    assert result['logs'] == []
    assert result['total'] == 0
    assert result['total_paginas'] == 0


def test_admin_audit_route_renders_for_admin(app_client):
    with app_client.session_transaction() as session:
        session.update(
            logado=True,
            usuario_id=1,
            usuario_role='admin',
            usuario_username='admin',
            csrf_token='csrf-test',
        )
    response = app_client.get('/atividades/auditoria')
    assert response.status_code == 200
    assert 'Auditoria e Segurança'.encode('utf-8') in response.data


def test_gravar_log_persists_structured_operational_event(temp_database):
    from data.logging import gravar_log

    event_id = gravar_log(
        'Cadastrou titular',
        usuario_id=1,
        ip='192.0.2.20',
        descricao='Titular de teste',
        contexto={'campo': 'nome', 'valor': 'Exemplo'},
    )
    row = database.executar_query(
        'SELECT event_id, domain, event_type, severity, contexto FROM logs WHERE event_id = ?',
        [event_id],
        fetch_one=True,
    )
    assert row is not None
    assert row['event_id'] == event_id
    assert row['domain'] == 'operacional'
    assert row['severity'] == 'INFO'
    assert 'Exemplo' in row['contexto']


def test_rotated_log_retention_removes_only_expired_files(tmp_path):
    import os
    import time
    from utils.logger_config import limpar_logs_antigos

    domain = tmp_path / 'operacional'
    domain.mkdir()
    active = domain / 'operacional.log'
    rotated = domain / 'operacional.log.2024-01-01'
    active.write_text('active\n', encoding='utf-8')
    rotated.write_text('old\n', encoding='utf-8')
    old_time = time.time() - (120 * 86400)
    os.utime(rotated, (old_time, old_time))
    result = limpar_logs_antigos(retention_days=90, base_dir=str(tmp_path))
    assert result['removidos'] == 1
    assert active.exists()
    assert not rotated.exists()



def test_status_edit_imports_unique_name_validation_and_preserves_self_name(temp_database):
    from data.process_status import add_status_processo, update_status_processo

    first_name = 'Status de teste A'
    second_name = 'Status de teste B'
    add_status_processo(first_name, '#111111')
    add_status_processo(second_name, '#222222')
    first = database.executar_query(
        'SELECT id FROM status_processo WHERE nome = ?', [first_name], fetch_one=True
    )
    second = database.executar_query(
        'SELECT id FROM status_processo WHERE nome = ?', [second_name], fetch_one=True
    )

    update_status_processo(first['id'], first_name, '#333333', 1)
    with pytest.raises(ValueError, match='já está em uso'):
        update_status_processo(first['id'], second_name, '#333333', 1)

    assert database.executar_query(
        'SELECT nome, hex_color FROM status_processo WHERE id = ?', [first['id']], fetch_one=True
    )['nome'] == first_name
    assert second['id'] != first['id']


def test_timed_rollover_lock_is_deferred_without_breaking_logging(tmp_path, monkeypatch):
    path = tmp_path / 'operacional.log'
    handler = SizeAndTimeRotatingFileHandler(
        str(path), when='midnight', interval=1, backupCount=0, max_bytes=0
    )

    def raise_windows_lock(_source, _destination):
        raise PermissionError(32, 'arquivo em uso')

    monkeypatch.setattr(handler, 'rotate', raise_windows_lock)
    try:
        handler._size_rollover = False
        handler.doRollover()
        assert handler.stream is not None
        assert handler._rollover_retry_after > 0
        handler.emit(logging.LogRecord('test', logging.INFO, __file__, 1, 'continua', (), None))
        handler.flush()
        assert path.exists()
    finally:
        handler.close()
