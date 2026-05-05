from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member, require_project_role, get_member_for_project
from app.models.article import Article
from app.models.media_asset import MediaAsset
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.media import MediaCreate, MediaUpdate, MediaPublic

router = APIRouter(tags=["media"])

_WRITE_ROLES = frozenset({"owner", "admin", "editor", "writer"})
_MANAGE_ROLES = frozenset({"owner", "admin", "editor"})


@router.get("/projects/{project_id}/media", response_model=list[MediaPublic])
def list_media(
    project_id: str,
    article_id: Optional[str] = None,
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    q = db.query(MediaAsset).filter(MediaAsset.project_id == project_id)
    if article_id:
        q = q.filter(MediaAsset.article_id == article_id)
    return q.order_by(MediaAsset.created_at.desc()).all()


@router.post("/projects/{project_id}/media/upload", response_model=MediaPublic, status_code=201)
def upload_media(
    project_id: str,
    data: MediaCreate,
    _actor: ProjectMember = Depends(require_project_role("owner", "admin", "editor", "writer")),
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
    return media


@router.patch("/media/{media_id}", response_model=MediaPublic)
def patch_media(
    media_id: str,
    data: MediaUpdate,
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

    db.delete(media)
    db.commit()
    return {"message": "Media deleted"}
