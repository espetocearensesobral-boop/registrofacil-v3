from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_PROCESS_LISTS = {
    'templates/processos/todos.html': 'todos',
    'templates/processos/hoje.html': 'hoje',
    'templates/processos/pendentes.html': 'pendentes',
    'templates/processos/em_andamento.html': 'em_andamento',
    'templates/processos/vinculados.html': 'vinculados',
}


def read(relative):
    return (ROOT / relative).read_text(encoding='utf-8')


def test_removed_root_templates_and_legacy_frontend_module_stay_removed():
    for relative in (
        'templates/todos.html',
        'templates/visualizar.html',
        'templates/em_andamento.html',
        'templates/hoje.html',
        'templates/pendentes.html',
        'templates/empresa.html',
        'static/js/notifications.js',
    ):
        assert not (ROOT / relative).exists(), relative


def test_active_process_report_actions_have_real_routes_and_safe_new_tabs():
    for relative, view_mode in ACTIVE_PROCESS_LISTS.items():
        text = read(relative)
        assert 'href="#"' not in text, relative
        assert "processos.gerar_pdf_lista" in text, relative
        assert "processos.imprimir_lista" in text, relative
        assert f"'view_mode': '{view_mode}'" in text, relative
        assert text.count('rel="noopener noreferrer"') >= 2, relative


def test_external_contact_links_use_noopener_and_close_labels_are_localized():
    for relative in (
        'templates/processos/visualizar.html',
        'templates/titulares/visualizar.html',
        'templates/apresentantes/visualizar.html',
    ):
        text = read(relative)
        assert 'target="_blank"' not in text or 'rel="noopener noreferrer"' in text, relative
        assert 'aria-label="Close"' not in text, relative

    assert 'aria-label="Close"' not in read('templates/admin/usuarios.html')
    for relative in ACTIVE_PROCESS_LISTS:
        assert 'aria-label="Close"' not in read(relative), relative


def test_removed_representante_selectors_and_dynamic_activity_link_contract():
    css = read('static/css/visual-system.css')
    atividades = read('templates/atividades.html')
    assert 'btn-excluir-representante' not in css
    assert 'btn-consultar-processo' in atividades
    assert "document.getElementById('btn-consultar-processo')" in atividades
    assert 'rel="noopener noreferrer"' in atividades



def test_all_active_new_tab_paths_use_opener_isolation():
    files = (
        'templates/processos/todos.html',
        'templates/processos/hoje.html',
        'templates/processos/pendentes.html',
        'templates/processos/em_andamento.html',
        'templates/processos/vinculados.html',
        'templates/processos/visualizar.html',
        'templates/titulares/index.html',
        'templates/titulares/visualizar.html',
        'templates/apresentantes/index.html',
        'templates/apresentantes/visualizar.html',
        'templates/atividades.html',
    )
    for relative in files:
        text = read(relative)
        assert 'target="_blank"' not in text or 'rel="noopener noreferrer"' in text, relative
        if 'window.open(' in text:
            assert 'noopener,noreferrer' in text, relative



def test_configuration_action_buttons_use_outline_semantic_contract():
    css = read('static/css/layout-standard.css')
    legacy_css = read('static/css/visual-system.css')
    html = read('templates/configuracoes.html')

    assert 'cfg-settings-action cfg-settings-action-edit' in html
    assert 'cfg-settings-action-danger' in html
    assert 'cfg-settings-action-success' in html
    assert 'body .cfg-ibtn' not in legacy_css
    assert 'cfg-ibtn edit' not in html
    assert 'cfg-destructive-toggle' not in html
    assert 'act-on' not in html
    assert 'html body #panel-status .cfg-row-actions .cfg-ibtn' not in css
    assert 'html body .cfg-settings-rebuild #panel-status .cfg-row-actions .cfg-settings-action' in html
    assert 'html body .cfg-settings-rebuild #panel-services .cfg-row-actions .cfg-settings-action' in html
    assert 'background: transparent !important;' in html
    assert 'color-mix(in srgb, var(--color-gold-primary' in html
    assert 'color-mix(in srgb, var(--color-error' in html
    assert 'color-mix(in srgb, var(--color-success' in html



def test_configuration_route_renders_namespaced_action_classes(app_client):
    with app_client.session_transaction() as session:
        session.update(
            logado=True,
            usuario_id=1,
            usuario_role='admin',
            usuario_username='admin',
            csrf_token='csrf-test',
        )

    response = app_client.get('/configuracoes/')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'cfg-settings-action cfg-settings-action-edit' in body
    assert 'cfg-settings-action-danger' in body
    assert 'cfg-settings-action-success' in body
    assert 'cfg-ibtn' not in body



def test_configuration_route_updates_status_without_missing_validator(app_client):
    import models

    with app_client.session_transaction() as session:
        session.update(
            logado=True,
            usuario_id=1,
            usuario_role='admin',
            usuario_username='admin',
            csrf_token='csrf-test',
        )

    status = models.executar_query(
        'SELECT id, nome, hex_color, ativo FROM status_processo ORDER BY id LIMIT 1',
        fetch_one=True,
    )
    assert status is not None
    updated_name = f"{status['nome']} (editado)"
    response = app_client.post(
        '/configuracoes/',
        data={
            'action': 'edit_status',
            'id': status['id'],
            'nome': updated_name,
            'hex_color': status['hex_color'],
            'ativo': str(status['ativo']),
            'csrf_token': 'csrf-test',
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    updated = models.executar_query(
        'SELECT nome FROM status_processo WHERE id = ?', [status['id']], fetch_one=True
    )
    assert updated['nome'] == updated_name
    assert updated_name in response.get_data(as_text=True)
