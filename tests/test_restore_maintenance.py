from pathlib import Path

from data import system_updates


def test_restore_maintenance_marker_is_created_and_removed(tmp_path, monkeypatch):
    marker = tmp_path / ".restore_maintenance"
    monkeypatch.setattr(system_updates, "RESTORE_MAINTENANCE_MARKER", str(marker))
    monkeypatch.setattr(system_updates.Config, "DATA_DIR", str(tmp_path), raising=False)

    system_updates.begin_restore_maintenance("teste")
    assert marker.read_text(encoding="utf-8") == "teste"
    assert system_updates.is_maintenance_active({"state": "idle"}) is True

    system_updates.end_restore_maintenance()
    assert not marker.exists()
