from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

LIST_TEMPLATES = [
    'templates/processos/todos.html',
    'templates/processos/hoje.html',
    'templates/processos/pendentes.html',
    'templates/processos/em_andamento.html',
    'templates/processos/vinculados.html',
    'templates/titulares/index.html',
    'templates/apresentantes/index.html',
    'templates/admin/usuarios.html',
    'templates/atividades.html',
]


def read(relative):
    return (ROOT / relative).read_text(encoding='utf-8')


def test_all_standardized_list_templates_use_continuous_scroll_markup():
    for relative in LIST_TEMPLATES:
        text = read(relative)
        assert 'data-infinite-scroll' in text, relative
        assert 'data-infinite-sentinel' in text, relative
        assert 'data-total-pages' in text, relative
        assert 'rf-pagination' not in text, relative
        assert 'class="pagination' not in text, relative


def test_standardized_filter_toolbars_do_not_expose_page_size_controls():
    for relative in [
        'templates/processos/_filter_toolbar.html',
        'templates/_cadastro_filter_toolbar.html',
        'templates/_users_filter_toolbar.html',
        'templates/_activity_filter_toolbar.html',
    ]:
        text = read(relative)
        assert 'Registros por página' not in text, relative
        assert 'por página' not in text, relative


def test_base_and_assets_expose_fixed_list_shell_contract():
    base = read('templates/base.html')
    css = read('static/css/layout-standard.css')
    js = read('static/js/infinite-tables.js')
    assert 'rf-list-page' in base
    assert 'infinite-tables.js' in base
    assert '#main-content.rf-list-page' in css
    assert 'overflow-y: auto !important' in css
    assert 'html {' in css and 'overflow-y: scroll !important' in css
    assert 'IntersectionObserver' in js
    assert 'data-infinite-scroll' in js
