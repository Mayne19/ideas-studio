"""Stockage des images générées : Supabase Storage si configuré, sinon
dossier local /uploads (dev). Hors ligne : upload Supabase simulé."""
from app.core.config import settings
from app.services import storage_service


def test_save_image_uses_supabase_upload_when_configured(monkeypatch):
    uploads = []

    def fake_upload(content, filename, project_id, content_type=None):
        uploads.append((content, filename, project_id, content_type))
        return f"https://x.supabase.co/storage/v1/object/public/ideas-media/{project_id}/abc.png"

    monkeypatch.setattr(storage_service, "is_configured", lambda: True)
    monkeypatch.setattr(storage_service, "upload_file", fake_upload)
    monkeypatch.setattr(storage_service, "optimize_image", lambda data, mime: (data, mime, None, None))

    stored = storage_service.save_image(b"png-bytes", "proj-1", "image/png")

    assert len(uploads) == 1
    content, filename, project_id, content_type = uploads[0]
    assert content == b"png-bytes" and project_id == "proj-1" and content_type == "image/png"
    assert filename.endswith(".png")
    assert stored["url"].startswith("https://x.supabase.co/storage/v1/object/public/")
    assert stored["byte_size"] == len(b"png-bytes")


def test_save_image_falls_back_to_local_uploads(monkeypatch, tmp_path):
    monkeypatch.setattr(storage_service, "is_configured", lambda: False)
    monkeypatch.setattr(storage_service, "optimize_image", lambda data, mime: (data, mime, None, None))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "APP_URL", "http://localhost:8000/")

    stored = storage_service.save_image(b"png-bytes", "proj-1", "image/png")

    assert stored["url"].startswith("http://localhost:8000/uploads/proj-1/")
    saved = tmp_path / "proj-1" / stored["filename"]
    assert saved.read_bytes() == b"png-bytes"


def test_optimize_image_converts_to_webp_when_pillow_available():
    import pytest

    Image = pytest.importorskip("PIL.Image")
    from io import BytesIO

    buf = BytesIO()
    Image.new("RGB", (2400, 1350), (31, 58, 95)).save(buf, format="PNG")
    data, mime, width, height = storage_service.optimize_image(buf.getvalue(), "image/png")
    assert mime == "image/webp"
    assert (width, height) == (1200, 675)
    assert data[:4] == b"RIFF"
