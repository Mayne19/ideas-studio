import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member, require_project_role, get_member_for_project
from app.models.article import Article
from app.models.media_asset import MediaAsset
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.media import MediaCreate, MediaUpdate, MediaPublic

router = APIRouter(tags=["media"])

def _set_public_url(item: MediaAsset, base: str):
    """Set public_url on a MediaAsset instance from its stored url."""
    url = item.url
    if url.startswith("/"):
        item.public_url = f"{base}{url}"
        return
    parsed = urlparse(url)
    if parsed.path.startswith("/uploads/"):
        item.public_url = f"{base}{parsed.path}"
    else:
        item.public_url = url

_WRITE_ROLES = frozenset({"owner", "admin", "editor", "writer"})
_MANAGE_ROLES = frozenset({"owner", "admin", "editor"})


@router.get("/projects/{project_id}/media", response_model=list[MediaPublic])
def list_media(
    project_id: str,
    article_id: Optional[str] = None,
    _member: ProjectMember = Depends(get_project_member),
    request: Request = None,
    db: Session = Depends(get_db),
):
    q = db.query(MediaAsset).filter(MediaAsset.project_id == project_id)
    if article_id:
        q = q.filter(MediaAsset.article_id == article_id)
    items = q.order_by(MediaAsset.created_at.desc()).all()
    base = str(request.base_url).rstrip("/")
    for item in items:
        _set_public_url(item, base)
    return items


@router.post("/projects/{project_id}/media/upload", response_model=MediaPublic, status_code=201)
async def upload_media(
    project_id: str,
    file: UploadFile = File(...),
    article_id: Optional[str] = Form(None),
    _actor: ProjectMember = Depends(require_project_role("owner", "admin", "editor", "writer")),
    request: Request = None,
    db: Session = Depends(get_db),
):
    if article_id:
        article = db.query(Article).filter(
            Article.id == article_id,
            Article.project_id == project_id,
        ).first()
        if not article:
            raise HTTPException(status_code=400, detail="Article not found in this project")

    ext = os.path.splitext(file.filename or "image.png")[1] or ".png"
    saved_name = f"{uuid.uuid4()}{ext}"
    upload_dir = os.path.join(settings.UPLOAD_DIR, project_id)
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, saved_name)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    url = f"/uploads/{project_id}/{saved_name}"

    media = MediaAsset(
        project_id=project_id,
        article_id=article_id,
        url=url,
        filename=file.filename or saved_name,
        mime_type=file.content_type or "image/png",
        size=len(content),
        alt_text=file.filename,
        source="upload",
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    base = str(request.base_url).rstrip("/")
    _set_public_url(media, base)
    return media


@router.post("/projects/{project_id}/media/upload-json", response_model=MediaPublic, status_code=201)
def upload_media_json(
    project_id: str,
    data: MediaCreate,
    _actor: ProjectMember = Depends(require_project_role("owner", "admin", "editor", "writer")),
    request: Request = None,
    db: Session = Depends(get_db),
):
    if data.article_id:
        article = db.query(Article).filter(
            Article.id == data.article_id,
            Article.project_id == project_id,
        ).first()
        if not article:
            raise HTTPException(status_code=400, detail="Article not found in this project")

    media = MediaAsset(
        project_id=project_id,
        article_id=data.article_id,
        url=data.url,
        filename=data.filename,
        mime_type=data.mime_type,
        size=data.size,
        alt_text=data.alt_text,
        caption=data.caption,
        source=data.source,
    )
    db.add(media)
    db.commit()
    db.refresh(media)
    base = str(request.base_url).rstrip("/")
    _set_public_url(media, base)
    return media


@router.patch("/media/{media_id}", response_model=MediaPublic)
def patch_media(
    media_id: str,
    data: MediaUpdate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db),
):
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    member = get_member_for_project(db, current_user.id, media.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot edit media")

    update_data = data.model_dump(exclude_unset=True)

    if "article_id" in update_data and update_data["article_id"] is not None:
        article = db.query(Article).filter(
            Article.id == update_data["article_id"],
            Article.project_id == media.project_id,
        ).first()
        if not article:
            raise HTTPException(status_code=400, detail="Article not found in this project")

    for field, value in update_data.items():
        setattr(media, field, value)

    media.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(media)
    base = str(request.base_url).rstrip("/")
    _set_public_url(media, base)
    return media


@router.delete("/media/{media_id}")
def delete_media(
    media_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    media = db.query(MediaAsset).filter(MediaAsset.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    member = get_member_for_project(db, current_user.id, media.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot delete media")

    if member.role == "writer":
        if media.article_id:
            article = db.query(Article).filter(Article.id == media.article_id).first()
            if article and article.status == "published":
                raise HTTPException(status_code=403, detail="Writers cannot delete media from published articles")

    filepath = os.path.join(settings.UPLOAD_DIR, media.project_id, os.path.basename(media.url))
    if os.path.exists(filepath):
        os.remove(filepath)

    db.delete(media)
    db.commit()
    return {"message": "Media deleted"}
