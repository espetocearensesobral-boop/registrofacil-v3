import logging
import sqlite3

import pytest

from data import database
from data.audit_logs import obter_eventos_unificados, obter_logs_seguranca
from utils.log_events import event_extra, sanitize_text
from utils.logger_config import RequestContextFilter, SizeAndTimeRotatingFileHandler


def test_log_event_sanitizes_secrets_and_has_correlation():
    assert 'supersecret' not in sanitize_text('senha=supersecret')
    extras = event_extra(domain='auth', event_type='login.failed', user_id=7, ip='192.0.2.10')
    assert len(extras['event_id']) == 20
    assert extras['domain'] == 'auth'
    assert extras['event_type'] == 'login.failed'
    assert extras['user_id'] == '7'


def test_sanitize_details_redacts_structured_secrets():
    from utils.log_events import sanitize_details

    result = sanitize_details({
        'password': 'supersecret',
        'nested': {'api_key': 'abc123'},
        'items': [{'token': 'token-value'}],
        'normal': 'preserved',
    })

    assert 'supersecret' not in result
    assert 'abc123' not in result
    assert 'token-value' not in result
    assert '[REDACTED]' in result
    assert 'preserved' in result


def test_sanitize_text_redacts_quoted_json_secrets():
    from utils.log_events import sanitize_text

    result = sanitize_text('{"password":"supersecret","smtp_password":"smtp-secret"}')

    assert 'supersecret' not in result
    assert 'smtp-secret' not in result
    assert result.count('[REDACTED]') == 2


def test_request_context_uses_one_id_and_trusted_proxy_ip(app_client):
    from flask import g
    from utils.log_events import current_ip, event_extra, request_id

    flask_app = app_client.application
    flask_app.config['TRUST_PROXY_HEADERS'] = True
    with flask_app.test_request_context(
        '/',
        base_url='http://127.0.0.1',
        headers={'X-Request-ID': 'request-123', 'X-Forwarded-For': '192.0.2.44, 10.0.0.1'},
    ):
        g.rf_request_id = None
        assert request_id() == 'request-123'
        assert event_extra()['request_id'] == 'request-123'
        assert current_ip() == '192.0.2.44'


def test_request_context_ignores_forwarded_ip_without_trust(app_client):
    from utils.log_events import current_ip

    flask_app = app_client.application
    flask_app.config['TRUST_PROXY_HEADERS'] = False
    with flask_app.test_request_context(
        '/',
        base_url='http://127.0.0.1',
        environ_base={'REMOTE_ADDR': '127.0.0.1'},
        headers={'X-Forwarded-For': '192.0.2.44'},
    ):
        assert current_ip() == '127.0.0.1'


def test_direct_logger_filter_reuses_request_context(app_client, tmp_path):
    import logging
    from utils.log_events import request_id
    from utils.logger_config import RequestContextFilter

    flask_app = app_client.application
    flask_app.config['TRUST_PROXY_HEADERS'] = True
    with flask_app.test_request_context(
        '/',
        base_url='http://127.0.0.1',
        environ_base={'REMOTE_ADDR': '127.0.0.1'},
        headers={'X-Request-ID': 'request-direct', 'X-Forwarded-For': '192.0.2.55'},
    ):
        assert request_id() == 'request-direct'
        record = logging.LogRecord('registrofacil.operacional', logging.INFO, __file__, 1, 'evento', (), None)
        assert RequestContextFilter().filter(record)
        assert record.request_id == 'request-direct'
        assert record.ip == '192.0.2.55'


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
            'login_attempts': {'event_id', 'request_id'},
        }.items():
            columns = {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
            assert expected <= columns


def test_catalog_persists_settings_and_process_actions(temp_database):
    from data.logging import gravar_log

    theme_event = gravar_log(
        'Alteração de Tema Visual',
        usuario_id=1,
        ip='192.0.2.10',
        descricao='Tema atualizado',
    )
    settings_event = gravar_log(
        'Configurações de backup atualizadas',
        usuario_id=1,
        ip='192.0.2.10',
    )

    rows = database.executar_query(
        "SELECT event_id, acao FROM logs WHERE event_id IN (?, ?) ORDER BY id",
        [theme_event, settings_event],
    )
    assert [row['event_id'] for row in rows] == [theme_event, settings_event]
    assert rows[0]['acao'].startswith('Alteração de Tema Visual')
    assert rows[1]['acao'] == 'Configurações de backup atualizadas'


def test_unified_action_filter_matches_legacy_action_with_details(temp_database):
    database.executar_query(
        "INSERT INTO logs (acao, contexto, timestamp) VALUES (?, ?, ?)",
        ['Cadastrou titular: nome=Exemplo', 'detalhes', '2026-08-22 10:00:00'],
    )

    result = obter_eventos_unificados({'acao': 'Cadastrou titular'})

    assert result['total'] == 1
    assert result['logs'][0]['acao'] == 'Cadastrou titular: nome=Exemplo'


def test_unified_event_query_merges_operational_admin_and_security_sources(temp_database):
    database.executar_query(
        "INSERT INTO logs (acao, contexto, usuario_id, ip, timestamp) VALUES (?, ?, ?, ?, ?)",
        ['Cadastrou titular', 'nome=Exemplo', None, '192.0.2.10', '2026-08-22 10:00:00'],
    )
    database.executar_query(
        "INSERT INTO auditoria_admin (acao, justificativa, ip, created_at) VALUES (?, ?, ?, ?)",
        ['alteração_role', 'Perfil atualizado', '192.0.2.11', '2026-08-22 10:01:00'],
    )
    database.executar_query(
        "INSERT INTO tentativas_acesso_nao_autorizado (tipo_tentativa, detalhes, ip, created_at) VALUES (?, ?, ?, ?)",
        ['acesso_admin_negado', 'Permissão insuficiente', '192.0.2.12', '2026-08-22 10:02:00'],
    )

    result = obter_eventos_unificados({}, pagina=1, por_pagina=10)
    assert result['total'] == 3
    assert {row['fonte'] for row in result['logs']} == {'atividade', 'auditoria', 'seguranca'}
    assert result['logs'][0]['fonte'] == 'seguranca'

    security_only = obter_eventos_unificados({'fonte': 'seguranca'}, pagina=1, por_pagina=10)
    assert security_only['total'] == 1
    assert security_only['logs'][0]['acao'] == 'acesso_admin_negado'


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
    response = app_client.get('/atividades/auditoria', follow_redirects=True)
    assert response.status_code == 200
    assert 'Atividades e Segurança'.encode('utf-8') in response.data
    assert 'Histórico unificado'.encode('utf-8') in response.data


def test_unified_events_are_rendered_inside_settings_and_old_sidebar_entry_is_gone(app_client):
    with app_client.session_transaction() as session:
        session.update(
            logado=True,
            usuario_id=1,
            usuario_role='admin',
            usuario_username='admin',
            csrf_token='csrf-test',
        )

    response = app_client.get('/configuracoes/?tab=atividades')
    assert response.status_code == 200
    assert 'Atividades e Segurança'.encode('utf-8') in response.data
    assert 'Histórico unificado'.encode('utf-8') in response.data
    assert 'Auditoria e Segurança'.encode('utf-8') not in response.data


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


def test_migration_015_preserves_logs_when_process_is_deleted(tmp_path, monkeypatch):
    import sqlite3
    from contextlib import contextmanager

    database_path = tmp_path / 'migration-015.db'
    conn = sqlite3.connect(database_path)
    conn.execute('PRAGMA foreign_keys = ON')
    conn.executescript('''
        CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, email TEXT);
        CREATE TABLE processos (id INTEGER PRIMARY KEY, numero_processo TEXT);
        CREATE TABLE logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acao TEXT NOT NULL,
            contexto TEXT,
            processo_id INTEGER,
            usuario_id INTEGER,
            ip TEXT,
            event_id TEXT,
            request_id TEXT,
            domain TEXT DEFAULT 'operacional',
            event_type TEXT DEFAULT 'legacy',
            entity_id TEXT,
            severity TEXT DEFAULT 'INFO',
            timestamp TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
            FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_logs_timestamp ON logs(timestamp DESC);
        INSERT INTO usuarios (id, nome, email) VALUES (1, 'Admin', 'admin@example.com');
        INSERT INTO processos (id, numero_processo) VALUES (7, 'PROC-7');
        INSERT INTO logs (acao, processo_id, usuario_id, entity_id) VALUES ('Editou processo', 7, 1, '7');
        PRAGMA user_version = 14;
    ''')
    conn.commit()
    conn.close()

    @contextmanager
    def temporary_connection():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON')
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    import data.migrations as migrations
    monkeypatch.setattr(migrations, 'get_sqlite_connection', temporary_connection)
    migrations.executar_migracoes_dados()

    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    fk = conn.execute('PRAGMA foreign_key_list(logs)').fetchall()
    process_fk = next(row for row in fk if row[3] == 'processo_id')
    assert process_fk[6].upper() == 'SET NULL'

    conn.execute('DELETE FROM processos WHERE id = 7')
    preserved = conn.execute('SELECT processo_id, entity_id FROM logs WHERE id = 1').fetchone()
    assert preserved['processo_id'] is None
    assert preserved['entity_id'] == '7'
    conn.close()


def test_admin_audit_uses_callers_connection_and_rolls_back(temp_database):
    from data.users import gravar_auditoria_admin

    conn = sqlite3.connect(str(temp_database))
    conn.row_factory = sqlite3.Row
    audit_id = gravar_auditoria_admin(
        admin_id=1,
        acao='alteracao_role',
        justificativa='Justificativa administrativa suficientemente detalhada.',
        ip='192.0.2.10',
        usuario_afetado_id=1,
        campo_alterado='role',
        valor_anterior='user',
        valor_novo='admin',
        event_id='audit-event-1',
        request_id='request-audit-1',
        connection=conn,
    )
    assert audit_id
    assert conn.execute('SELECT COUNT(*) FROM auditoria_admin').fetchone()[0] == 1
    conn.rollback()
    conn.close()

    assert database.executar_query(
        "SELECT COUNT(*) AS total FROM auditoria_admin WHERE event_id = ?",
        ['audit-event-1'],
        fetch_one=True,
    )['total'] == 0
