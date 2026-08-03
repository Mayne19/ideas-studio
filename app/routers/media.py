import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import MemberView, get_current_user, get_project_member, require_project_role, get_member_for_project
from app.models.content import Article, ArticleMedia, MediaAsset
from app.models.reference import MediaRole
from app.models.core import User
from app.schemas.media import MediaCreate, MediaUpdate, MediaPublic
from app.services import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["media"])

_WRITE_ROLES = frozenset({"owner", "admin", "editor", "designer"})

# Whitelist des types MIME acceptés
ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "image/gif", "image/svg+xml",
}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _public_url(url: str, base: str) -> str:
    if url.startswith("/"):
        return f"{base}{url}"
    parsed = urlparse(url)
    if parsed.path.startswith("/uploads/"):
        return f"{base}{parsed.path}"
    return url


def _article_id_for(db: Session, media_id: str) -> str | None:
    return db.execute(
        select(ArticleMedia.article_id).where(ArticleMedia.media_id == media_id).limit(1)
    ).scalar_one_or_none()


def _to_public(db: Session, media: MediaAsset, base: str) -> MediaPublic:
    return MediaPublic(
        id=media.id,
        project_id=media.project_id,
        article_id=_article_id_for(db, media.id),
        url=media.url,
        public_url=_public_url(media.url, base),
        filename=media.filename,
        mime_type=media.mime_type,
        size=media.byte_size,
        alt_text=media.alt_text,
        caption=media.caption,
        source=media.source,
        created_at=media.created_at,
    )


def _link_article(db: Session, media_id: str, article_id: str | None) -> None:
    db.execute(ArticleMedia.__table__.delete().where(ArticleMedia.media_id == media_id))
    if article_id:
        db.add(ArticleMedia(article_id=article_id, media_id=media_id, role=MediaRole.INLINE, position=0))


@router.get("/projects/{project_id}/media", response_model=list[MediaPublic])
def list_media(
    project_id: str,
    article_id: Optional[str] = None,
    _member: MemberView = Depends(get_project_member),
    request: Request = None,
    db: Session = Depends(get_db),
):
    query = select(MediaAsset).where(MediaAsset.project_id == project_id)
    if article_id:
        query = query.join(ArticleMedia, ArticleMedia.media_id == MediaAsset.id).where(ArticleMedia.article_id == article_id)
    items = db.execute(query.order_by(MediaAsset.created_at.desc())).scalars().all()
    base = str(request.base_url).rstrip("/")
    return [_to_public(db, item, base) for item in items]


@router.post("/projects/{project_id}/media/upload", response_model=MediaPublic, status_code=201)
async def upload_media(
    project_id: str,
    file: UploadFile = File(...),
    article_id: Optional[str] = Form(None),
    _actor: MemberView = Depends(require_project_role("owner", "admin", "editor", "designer")),
    request: Request = None,
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Type de fichier non autorisé: {file.content_type}. "
                   f"Types acceptés: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )

    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux. Maximum: {MAX_FILE_SIZE_MB} Mo"
        )

    if article_id:
        article = db.get(Article, article_id)
        if not article or article.project_id != project_id:
            raise HTTPException(status_code=400, detail="Article not found in this project")

    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    saved_name = f"{uuid.uuid4()}{ext}"

    if storage_service.is_configured():
        try:
            url = storage_service.upload_file(
                file_content=content,
                filename=file.filename or saved_name,
                project_id=project_id,
                content_type=file.content_type,
            )
        except Exception as exc:
            logger.error("Supabase Storage upload failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail="Échec de l'upload vers le stockage permanent. Réessayez ou contactez l'administrateur.",
            )
    else:
        upload_dir = os.path.join(settings.UPLOAD_DIR, project_id)
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, saved_name)

        with open(filepath, "wb") as f:
            f.write(content)

        url = f"/uploads/{project_id}/{saved_name}"

    media = MediaAsset(
        project_id=project_id,
        url=url,
        filename=file.filename or saved_name,
        mime_type=file.content_type or "image/png",
        byte_size=len(content),
        alt_text=file.filename,
        source="upload",
    )
    db.add(media)
    db.flush()
    _link_article(db, media.id, article_id)
    db.commit()
    db.refresh(media)
    base = str(request.base_url).rstrip("/")
    return _to_public(db, media, base)


@router.post("/projects/{project_id}/media/upload-json", response_model=MediaPublic, status_code=201)
def upload_media_json(
    project_id: str,
    data: MediaCreate,
    _actor: MemberView = Depends(require_project_role("owner", "admin", "editor", "designer")),
    request: Request = None,
    db: Session = Depends(get_db),
):
    if data.article_id:
        article = db.get(Article, data.article_id)
        if not article or article.project_id != project_id:
            raise HTTPException(status_code=400, detail="Article not found in this project")

    media = MediaAsset(
        project_id=project_id,
        url=data.url,
        filename=data.filename,
        mime_type=data.mime_type,
        byte_size=data.size,
        alt_text=data.alt_text,
        caption=data.caption,
        source=data.source,
    )
    db.add(media)
    db.flush()
    _link_article(db, media.id, data.article_id)
    db.commit()
    db.refresh(media)
    base = str(request.base_url).rstrip("/")
    return _to_public(db, media, base)


@router.patch("/media/{media_id}", response_model=MediaPublic)
def patch_media(
    media_id: str,
    data: MediaUpdate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db),
):
    media = db.get(MediaAsset, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    member = get_member_for_project(db, current_user.id, media.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot edit media")

    update_data = data.model_dump(exclude_unset=True)

    if "article_id" in update_data:
        article_id = update_data.pop("article_id")
        if article_id is not None:
            article = db.get(Article, article_id)
            if not article or article.project_id != media.project_id:
                raise HTTPException(status_code=400, detail="Article not found in this project")
        _link_article(db, media.id, article_id)

    for field, value in update_data.items():
        setattr(media, field, value)

    db.commit()
    db.refresh(media)
    base = str(request.base_url).rstrip("/")
    return _to_public(db, media, base)


@router.delete("/media/{media_id}")
def delete_media(
    media_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = db.get(MediaAsset, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    member = get_member_for_project(db, current_user.id, media.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot delete media")

    if not storage_service.delete_file(media.url):
        filepath = os.path.join(settings.UPLOAD_DIR, media.project_id, os.path.basename(media.url))
        if os.path.exists(filepath):
            os.remove(filepath)

    db.delete(media)
    db.commit()
    return {"message": "Media deleted"}
