import hashlib
import io
import json
import zipfile

import pytest

from data import update_launcher


class FakeResponse:
    def __init__(self, payload):
        self._stream = io.BytesIO(payload)
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self._stream.read(size)


def make_zip(contents=b"release-content"):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("app.txt", contents)
    return stream.getvalue()


def test_download_package_validates_sha256(tmp_path, monkeypatch):
    package = make_zip()
    expected = hashlib.sha256(package).hexdigest()
    monkeypatch.setattr(update_launcher, "urlopen", lambda *_args, **_kwargs: FakeResponse(package))

    output = update_launcher.download_package(
        "https://github.com/example/release.zip",
        tmp_path / "package.zip",
        expected,
    )

    assert output.read_bytes() == package


def test_download_package_rejects_hash_mismatch(tmp_path, monkeypatch):
    package = make_zip()
    monkeypatch.setattr(update_launcher, "urlopen", lambda *_args, **_kwargs: FakeResponse(package))

    with pytest.raises(ValueError, match="SHA-256 divergente"):
        update_launcher.download_package(
            "https://github.com/example/release.zip",
            tmp_path / "package.zip",
            "a" * 64,
        )


def test_extract_package_rejects_path_traversal(tmp_path):
    package_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(package_path, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")

    with pytest.raises(ValueError, match="Entrada insegura"):
        update_launcher.extract_package(package_path, tmp_path / "staging")


def test_activate_release_writes_atomic_pointer(tmp_path):
    layout = update_launcher.ReleaseLayout(tmp_path / "updates")
    layout.ensure()
    (layout.releases / "3.19.0").mkdir(parents=True)

    release = update_launcher.activate_release(layout, "3.19.0")

    assert release.name == "3.19.0"
    pointer = json.loads(layout.current_pointer.read_text(encoding="utf-8"))
    assert pointer["version"] == "3.19.0"


def test_backup_installation_preserves_database_uploads_and_keys(tmp_path):
    layout = update_launcher.ReleaseLayout(tmp_path / "updates")
    layout.ensure()
    db = tmp_path / "registrofacil.db"
    db.write_bytes(b"database")
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    (uploads / "file.txt").write_text("upload", encoding="utf-8")
    key = tmp_path / ".secret_key"
    key.write_text("secret", encoding="utf-8")

    backup = update_launcher.backup_installation(layout, db, uploads, (key,))

    assert (backup / db.name).read_bytes() == b"database"
    assert (backup / "uploads" / "file.txt").read_text(encoding="utf-8") == "upload"
    assert (backup / "keys" / key.name).read_text(encoding="utf-8") == "secret"
