from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_backup_settings_form_declares_save_action_and_required_fields():
    template = read("templates/backup.html")
    form_start = template.index('id="form-all-backup-settings"')
    form_end = template.index("</form>", form_start)
    form = template[form_start:form_end]

    assert 'name="action" value="update_backup_settings"' in form
    assert 'name="auto_backup_enabled"' in form
    assert 'name="backup_frequency"' in form
    assert 'name="backup_time"' in form
    assert 'name="backup_days[]"' in form
    assert 'name="backup_day_of_month"' in form
    assert 'data-rf-submit-state' in form


def test_global_submit_handler_preserves_named_submitter_values():
    main_js = read("static/js/main.js")

    assert "const submitterName = submitButton.getAttribute('name')" in main_js
    assert "submitterProxy.name = submitterName" in main_js
    assert "submitterProxy.dataset.rfSubmitProxy = 'true'" in main_js
    assert "form.querySelectorAll('[data-rf-submit-proxy]').forEach(proxy => proxy.remove())" in main_js



def test_backup_settings_modal_uses_compact_dialog_contract():
    template = read("templates/backup.html")

    assert 'class="modal-dialog backup-settings-dialog modal-dialog-centered modal-dialog-scrollable"' in template
    assert 'width: min(100% - 1.5rem, 44rem)' in template
    assert '#backupSettingsModal .backup-settings-body' in template
    assert '#backupSettingsModal .cfg-card {\n    margin-bottom: 6px;' in template
    assert '#backupSettingsModal .cfg-inline-end .cfg-sbtn' in template
