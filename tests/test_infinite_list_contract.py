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
        assert 'data-list-scroll-mode="internal"' not in text, relative


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


def test_todos_processos_uses_internal_first_mode_with_ten_record_batch():
    template = read('templates/processos/todos.html')
    route = read('routes/processos.py')
    js = read('static/js/infinite-tables.js')
    css = read('static/css/layout-standard.css')
    assert 'data-list-scroll-mode="internal-first"' in template
    assert "request.args.get('registros_por_pagina', 10, type=int)" in route
    assert 'const naturalPageScroll' in js
    assert 'activateMainScroll' not in js
    assert 'window.addEventListener(\'scroll\', onWindowScroll' in js
    assert 'documentNearEnd' in js
    assert 'max-height: none !important' in css
    assert 'overflow-y: visible !important' in css
    assert 'overflow: visible !important' in css


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
    assert 'list.dataset.listScrollMode !== \'internal\'' in js
    assert 'Todas as listas padronizadas' in css


def test_cadastro_tables_expose_ids_and_last_record_data_contract():
    titulares = read('templates/titulares/index.html')
    apresentantes = read('templates/apresentantes/index.html')
    for text in (titulares, apresentantes):
        assert 'data-label="ID"' in text
        assert '>ID<' in text or '>ID{{' in text
        assert 'data-label="Último Registro"' in text
        assert 'ultimo_registro_id' in text
        assert 'ultimo_registro_matricula' in text
    registries = read('data/registries.py')
    assert 'ultimo.id as ultimo_registro_id' in registries
    assert 'ultimo_registro_matricula' in registries


def test_process_lists_order_entry_deadline_status_in_headers_and_rows():
    for relative in [
        'templates/processos/todos.html',
        'templates/processos/hoje.html',
        'templates/processos/em_andamento.html',
        'templates/processos/pendentes.html',
        'templates/processos/vinculados.html',
    ]:
        text = read(relative)
        entry = text.find('data-label="Entrada"')
        deadline = text.find('data-label="Prazo"')
        status = text.find('data-label="Status"')
        assert -1 not in (entry, deadline, status), relative
        assert entry < deadline < status, relative
        assert text.count('Entrada') >= 1, relative
        assert text.count('Prazo') >= 1, relative
        assert text.count('Status') >= 1, relative



def test_activity_table_uses_proportional_columns_and_wraps_only_long_content():
    template = read('templates/atividades.html')
    css = read('static/css/layout-standard.css')

    for column in (
        'activity-col-id',
        'activity-col-user',
        'activity-col-action',
        'activity-col-process',
        'activity-col-ip',
        'activity-col-datetime',
    ):
        assert f'class="{column}"' in template

    assert '.rf-table.table-atividades {' in css
    assert 'table-layout: fixed !important' in css
    assert 'col.activity-col-user { width: 14%' in css
    assert 'col.activity-col-action { width: 48%' in css
    assert 'td[data-label="Usuário"]' in css
    assert 'td[data-label="Ação"] .btn-acao-clicavel' in css
    assert 'min-width: 0 !important' in css
