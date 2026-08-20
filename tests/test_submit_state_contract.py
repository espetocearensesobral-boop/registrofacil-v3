from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_custom_forms_opt_out_of_global_submit_state_handler():
    forms = {
        "templates/processos/novo.html": 'id="form-processo"',
        "templates/processos/editar.html": 'id="form-processo"',
        "templates/apresentantes/novo.html": 'id="form-apresentante"',
        "templates/apresentantes/editar.html": 'id="form-apresentante"',
        "templates/titulares/novo.html": 'id="form-titular"',
        "templates/titulares/editar.html": 'id="form-titular"',
        "templates/admin/editar_usuario.html": 'id="form-edit-user"',
        "templates/admin/gerenciar_usuario.html": 'id="form-gerenciar-usuario"',
        "templates/admin/perfil_admin.html": 'id="form-gerenciar-usuario"',
    }

    for relative_path, form_marker in forms.items():
        template = read(relative_path)
        form_start = template.index(form_marker)
        form_end = template.index(">", form_start)
        form_tag = template[template.rfind("<form", 0, form_start):form_end]
        assert "data-rf-submit-managed" in form_tag, relative_path
        assert "data-rf-submit-state" in form_tag, relative_path


def test_global_submit_state_has_safe_reset_and_respects_custom_handlers():
    main_js = read("static/js/main.js")

    assert "function restaurarEstadoDeEnvio" in main_js
    assert "window.resetSubmitState" in main_js
    assert "form.hasAttribute('data-rf-submit-managed')" in main_js
    assert "window.addEventListener('pageshow'" in main_js
    assert "delete button.dataset.rfSubmitting" in main_js
    assert "delete button.dataset.rfOriginalHtml" in main_js
