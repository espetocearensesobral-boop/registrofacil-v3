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


def test_process_lists_use_global_title_and_white_integrated_filter_shell():
    css = read('static/css/layout-standard.css')
    for relative in LIST_TEMPLATES[:5]:
        text = read(relative)
        assert 'process-list-card' in text, relative
        assert 'rf-card-header' not in text, relative
        assert 'rf-badge count' not in text, relative
        assert 'processos/_filter_toolbar.html' in text, relative

    assert 'background: var(--rf-surface-card, #FFFFFF) !important;' in css
    assert 'background: var(--rf-surface, #fff) !important;' in css
    assert 'process-list-card .table-processos' in css



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


def test_cadastros_auditoria_and_users_use_clean_white_list_shell():
    css = read('static/css/layout-standard.css')
    templates = (
        'templates/apresentantes/index.html',
        'templates/titulares/index.html',
        'templates/auditoria.html',
        'templates/admin/usuarios.html',
    )

    for relative in templates:
        text = read(relative)
        assert 'rf-clean-list-card' in text, relative
        assert 'rf-card-header' not in text, relative
        assert 'rf-badge count' not in text, relative

    assert '.rf-clean-list-card' in css
    assert 'background: var(--rf-surface-card, #FFFFFF) !important;' in css
    assert 'table-apresentantes' in css
    assert 'table-titulares' in css
    assert 'table-usuarios' in css
    assert 'table-auditoria' in css
    assert '.rf-clean-list-card .tbl-actions .tbl-btn' in css
    assert '.rf-clean-list-card .tbl-actions .tbl-btn.view' in css
    assert '.rf-clean-list-card .tbl-actions .tbl-btn.edit' in css
    assert '.rf-clean-list-card .tbl-actions .tbl-btn.del' in css
    assert '#main-content > .cadastro-list-card .table-titulares .tbl-actions .tbl-btn.edit' in css
    assert '#main-content > .cadastro-list-card .table-apresentantes .tbl-actions .tbl-btn.del' in css
    assert '.cfg-settings-rebuild #panel-status .cfg-row-actions .cfg-ibtn.edit' in css
    assert '.cfg-settings-rebuild #panel-services .cfg-row-actions .cfg-ibtn.act-on' in css


def test_process_action_buttons_have_complete_semantic_visual_contract():
    css = read('static/css/layout-standard.css')
    templates = (
        'templates/processos/todos.html',
        'templates/processos/hoje.html',
        'templates/processos/pendentes.html',
        'templates/processos/em_andamento.html',
        'templates/processos/vinculados.html',
    )

    for relative in templates:
        text = read(relative)
        assert 'tbl-btn view' in text, relative
        assert 'tbl-btn edit' in text, relative
        assert 'tbl-btn del' in text, relative
        assert 'bi-eye' in text, relative
        assert 'bi-pencil' in text or 'bi-pencil-square' in text, relative
        assert 'bi-trash' in text, relative

    assert '.process-list-card .tbl-actions .tbl-btn' in css
    assert '.tbl-actions .tbl-btn.view' in css
    assert '.tbl-actions .tbl-btn.edit' in css
    assert '.tbl-actions .tbl-btn.del' in css
    assert 'visibility: visible !important' in css
    assert 'opacity: 1 !important' in css


def test_complementary_action_groups_share_spacing_and_visibility_contract():
    css = read('static/css/layout-standard.css')
    main_js = read('static/js/main.js')
    config_template = read('templates/configuracoes.html')

    assert 'rf-search-action-view' in main_js
    assert 'rf-search-action-print' in main_js
    assert 'rf-search-action-download' in main_js
    assert '#globalSearchModal .rf-process-report-actions .rf-search-action' in css
    assert 'visibility: visible !important' in css
    assert 'opacity: 1 !important' in css
    assert '.cfg-settings-rebuild .cfg-row-actions' in css
    assert '#panel-status .cfg-actions-cell' in css
    assert '#panel-services .cfg-actions-cell' in css
    assert 'id="panel-status"' in config_template
    assert 'id="panel-services"' in config_template



def test_disabled_cadastro_actions_keep_semantic_contrast_without_reenabling_business_actions():
    css = read('static/css/layout-standard.css')
    titulares = read('templates/titulares/index.html')
    apresentantes = read('templates/apresentantes/index.html')

    for text in (titulares, apresentantes):
        assert 'class="tbl-btn edit is-disabled"' in text
        assert 'class="tbl-btn del is-disabled"' in text

    assert '.tbl-btn.edit.is-disabled' in css
    assert '.tbl-btn.del.is-disabled' in css
    assert 'color: var(--color-gold-dark, #8B6332) !important;' in css
    assert 'color: var(--color-error, #98424C) !important;' in css
    assert 'pointer-events: none !important;' in css
    assert 'cursor: not-allowed !important;' in css

    # Os controles continuam visualmente identificáveis, mas não são reativados.
    assert 'opacity: .82 !important;' in css



def test_process_list_report_modals_use_real_export_and_print_routes():
    expected_views = {
        'templates/processos/todos.html': 'todos',
        'templates/processos/hoje.html': 'hoje',
        'templates/processos/pendentes.html': 'pendentes',
        'templates/processos/em_andamento.html': 'em_andamento',
        'templates/processos/vinculados.html': 'vinculados',
    }

    for relative, view_mode in expected_views.items():
        text = read(relative)
        assert 'href="#"' not in text, relative
        assert "processos.gerar_pdf_lista" in text, relative
        assert "processos.imprimir_lista" in text, relative
        assert f"'view_mode': '{view_mode}'" in text, relative
