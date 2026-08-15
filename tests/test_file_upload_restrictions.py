from io import BytesIO
from pathlib import Path

import pytest
from werkzeug.datastructures import FileStorage, MultiDict

from config import Config
from routes import processos
from utils import file_uploads


PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _upload(name, content, content_type=None):
    return FileStorage(
        stream=BytesIO(content),
        filename=name,
        content_type=content_type,
    )


def test_policy_allows_only_pdf_jpeg_jpg_and_png():
    assert set(Config.ALLOWED_EXTENSIONS) == {"pdf", "jpg", "jpeg", "png"}


def test_mime_must_match_real_content(tmp_path, monkeypatch):
    monkeypatch.setattr(processos, "get_upload_folder", lambda: str(tmp_path))
    monkeypatch.setattr(processos, "inserir_anexo_processo", lambda **_kwargs: None)

    files = MultiDict(
        [
            ("anexos[]", _upload("documento.pdf", PDF_BYTES, "application/pdf")),
            ("anexos[]", _upload("documento.jpg", PDF_BYTES, "image/jpeg")),
        ]
    )

    saved, rejected = processos.processar_anexos_upload(files, 1, 1, object())

    assert saved == ["documento.pdf"]
    assert any("documento.jpg" in item for item in rejected)
    assert len(list(Path(tmp_path).iterdir())) == 1
    assert next(Path(tmp_path).iterdir()).suffix == ".pdf"


def test_unsupported_extension_is_rejected_before_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(processos, "get_upload_folder", lambda: str(tmp_path))

    files = MultiDict(
        [("anexos[]", _upload("arquivo.docx", PDF_BYTES, "application/pdf"))]
    )

    saved, rejected = processos.processar_anexos_upload(files, 1, 1, object())

    assert saved == []
    assert any("Extensão não permitida" in item for item in rejected)
    assert list(Path(tmp_path).iterdir()) == []


def test_db_failure_removes_final_and_temporary_files(tmp_path, monkeypatch):
    monkeypatch.setattr(processos, "get_upload_folder", lambda: str(tmp_path))

    def fail_insert(**_kwargs):
        raise RuntimeError("falha simulada no banco")

    monkeypatch.setattr(processos, "inserir_anexo_processo", fail_insert)
    files = MultiDict(
        [("anexos[]", _upload("documento.pdf", PDF_BYTES, "application/pdf"))]
    )

    saved, rejected = processos.processar_anexos_upload(files, 1, 1, object())

    assert saved == []
    assert rejected
    assert list(Path(tmp_path).iterdir()) == []


def test_profile_image_helper_rejects_pdf_even_with_image_extension(tmp_path):
    upload = _upload("avatar.png", PDF_BYTES, "image/png")

    with pytest.raises(ValueError, match="conteúdo do arquivo"):
        file_uploads.handle_image_upload(
            uploaded_file=upload,
            current_filename=None,
            target_folder=str(tmp_path),
            allowed_extensions=["jpg", "jpeg", "png"],
            max_size_mb=2,
            prefix="teste",
        )

    assert list(Path(tmp_path).iterdir()) == []


def test_profile_image_helper_rejects_gif_extension(tmp_path):
    upload = _upload("avatar.gif", b"GIF89a", "image/gif")

    with pytest.raises(ValueError, match="Formato de imagem inválido"):
        file_uploads.handle_image_upload(
            uploaded_file=upload,
            current_filename=None,
            target_folder=str(tmp_path),
            allowed_extensions=["jpg", "jpeg", "png"],
            max_size_mb=2,
            prefix="teste",
        )

    assert list(Path(tmp_path).iterdir()) == []


def test_image_mime_aliases_do_not_allow_legacy_formats():
    assert set(file_uploads.IMAGE_MIME_ALIASES) == {"jpg", "jpeg", "png"}
    assert processos.mime_valido_para_extensao("gif", "image/gif") is False
    assert processos.mime_valido_para_extensao("pdf", "image/png") is False
