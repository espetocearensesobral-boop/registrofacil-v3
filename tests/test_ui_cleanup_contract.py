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
