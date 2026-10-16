"""
StorageService — Stockage permanent des fichiers sur Supabase Storage.
Remplace le stockage sur disque local (éphémère sur Render).
"""
from __future__ import annotations
import logging
import mimetypes
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """True si Supabase Storage est configuré (sinon, repli sur le disque local)."""
    from app.core.config import settings
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)


def _get_client():
    """Retourne le client Supabase initialisé."""
    from app.core.config import settings
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def upload_file(
    file_content: bytes,
    filename: str,
    project_id: str,
    content_type: str | None = None,
) -> str:
    """
    Upload un fichier sur Supabase Storage.

    Args:
        file_content : contenu du fichier en bytes
        filename     : nom du fichier original
        project_id   : ID du projet (pour organiser les fichiers par dossier)
        content_type : MIME type du fichier

    Returns:
        URL publique permanente du fichier
    """
    from app.core.config import settings

    # Générer un nom unique pour éviter les collisions
    ext = Path(filename).suffix or ".png"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    storage_path = f"{project_id}/{unique_name}"

    # Détecter le content type si non fourni
    if not content_type:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    client = _get_client()

    # Upload sur Supabase Storage
    client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).upload(
        path=storage_path,
        file=file_content,
        file_options={"content-type": content_type, "upsert": "true"},
    )

    # Construire l'URL publique permanente
    public_url = (
        f"{settings.SUPABASE_URL}/storage/v1/object/public/"
        f"{settings.SUPABASE_STORAGE_BUCKET}/{storage_path}"
    )

    logger.info("File uploaded to Supabase Storage: %s", public_url)
    return public_url


def delete_file(url: str) -> bool:
    """
    Supprime un fichier depuis son URL publique Supabase Storage.
    Retourne True si supprimé, False sinon.
    """
    from app.core.config import settings

    try:
        # Extraire le path depuis l'URL
        bucket_prefix = (
            f"{settings.SUPABASE_URL}/storage/v1/object/public/"
            f"{settings.SUPABASE_STORAGE_BUCKET}/"
        )
        if not settings.SUPABASE_URL or not url.startswith(bucket_prefix):
            logger.debug("URL not from Supabase Storage, skipping delete: %s", url)
            return False

        storage_path = url.replace(bucket_prefix, "")
        client = _get_client()
        client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).remove([storage_path])
        logger.info("File deleted from Supabase Storage: %s", storage_path)
        return True
    except Exception as exc:
        logger.warning("Failed to delete file from Supabase Storage: %s", exc)
        return False


# ── Images générées ────────────────────────────────────────────────────────

GENERATED_IMAGE_MAX_WIDTH = 1200


def optimize_image(data: bytes, mime_type: str, max_width: int = GENERATED_IMAGE_MAX_WIDTH) -> tuple[bytes, str, int | None, int | None]:
    """Redimensionne à `max_width` px de large et convertit en WebP si Pillow
    est installé ; sinon renvoie l'image telle quelle (dimensions inconnues).
    Retourne (octets, mime, largeur, hauteur)."""
    try:
        from PIL import Image
    except ImportError:
        return data, mime_type, None, None
    try:
        from io import BytesIO

        with Image.open(BytesIO(data)) as source:
            img = source.convert("RGB")
        if img.width > max_width:
            img = img.resize((max_width, round(img.height * max_width / img.width)), Image.LANCZOS)
        out = BytesIO()
        img.save(out, format="WEBP", quality=82, method=6)
        return out.getvalue(), "image/webp", img.width, img.height
    except Exception as exc:
        logger.warning("Conversion WebP impossible (%s) — image d'origine conservée", exc)
        return data, mime_type, None, None


def save_image(data: bytes, project_id: str, mime_type: str = "image/png", basename: str = "illustration") -> dict:
    """Stocke une image (générée) de façon permanente : Supabase Storage si
    configuré, sinon le dossier local UPLOAD_DIR servi sous /uploads (dev).
    Retourne url, filename, mime_type, byte_size, width, height."""
    import os

    from app.core.config import settings

    data, mime_type, width, height = optimize_image(data, mime_type)
    ext = ".webp" if mime_type == "image/webp" else (mimetypes.guess_extension(mime_type) or ".png")
    if is_configured():
        url = upload_file(data, f"{basename}{ext}", project_id, content_type=mime_type)
        filename = url.rsplit("/", 1)[-1]
    else:
        filename = f"{uuid.uuid4().hex}{ext}"
        upload_dir = os.path.join(settings.UPLOAD_DIR, project_id)
        os.makedirs(upload_dir, exist_ok=True)
        with open(os.path.join(upload_dir, filename), "wb") as fh:
            fh.write(data)
        url = f"{settings.APP_URL.rstrip('/')}/uploads/{project_id}/{filename}"
    return {
        "url": url,
        "filename": filename,
        "mime_type": mime_type,
        "byte_size": len(data),
        "width": width,
        "height": height,
    }
