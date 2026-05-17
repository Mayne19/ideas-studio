from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member, require_project_role, get_member_for_project
from app.models.user import User
from app.models.project_member import ProjectMember
from app.models.article import WRITER_EDITABLE_STATUSES
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticlePublic, ArticleScheduleRequest
from app.services.article_service import (
    create_article,
    delete_article,
    get_article_by_id,
    list_articles,
    update_article,
    publish_article,
    promote_article,
    schedule_article,
    unpublish_article,
)

router = APIRouter(tags=["articles"])

_MANAGE_ROLES = ("owner", "admin", "editor")
_ALL_WRITE_ROLES = ("owner", "admin", "editor", "writer")


@router.get("/projects/{project_id}/articles", response_model=list[ArticlePublic])
def list_articles_route(
    project_id: str,
    status: Optional[str] = None,
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    published_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    return list_articles(db, project_id, status=status, category_id=category_id, search=search,
                         published_only=published_only, limit=limit, offset=offset)


@router.post("/projects/{project_id}/articles", response_model=ArticlePublic, status_code=201)
def create_article_route(
    project_id: str,
    data: ArticleCreate,
    member: ProjectMember = Depends(require_project_role(*_ALL_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return create_article(db, data, project_id)


@router.get("/articles/{article_id}", response_model=ArticlePublic)
def get_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    return article


@router.patch("/articles/{article_id}", response_model=ArticlePublic)
def patch_article_route(
    article_id: str,
    data: ArticleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot edit articles")
    if member.role == "writer" and article.status not in WRITER_EDITABLE_STATUSES:
        raise HTTPException(status_code=403, detail="Writers can only edit draft articles")
    return update_article(db, article, data)


@router.post("/articles/{article_id}/promote", response_model=ArticlePublic)
def promote_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to promote")
    if article.status != "published":
        raise HTTPException(status_code=400, detail="Only published articles can be promoted")
    return promote_article(db, article)


@router.post("/articles/{article_id}/publish", response_model=ArticlePublic)
def publish_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to publish")
    return publish_article(db, article)


@router.post("/articles/{article_id}/schedule-update", response_model=ArticlePublic)
def schedule_update_route(
    article_id: str,
    data: ArticleScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to schedule update")
    if article.status != "published":
        raise HTTPException(status_code=400, detail="Only published articles can have scheduled updates")
    article.scheduled_update_at = data.scheduled_at
    article.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    db.commit()
    db.refresh(article)
    return article


@router.post("/articles/{article_id}/schedule", response_model=ArticlePublic)
def schedule_article_route(
    article_id: str,
    data: ArticleScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to schedule")
    return schedule_article(db, article, data.scheduled_at)


@router.post("/articles/{article_id}/mark-ready", response_model=ArticlePublic)
def mark_ready_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot change article status")
    if member.role == "writer" and article.status == "published":
        raise HTTPException(status_code=403, detail="Writers cannot change published articles")
    article.status = "ready_to_publish"
    from datetime import datetime, timezone
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


@router.post("/articles/{article_id}/archive", response_model=ArticlePublic)
def archive_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to archive")
    article.status = "archived"
    from datetime import datetime, timezone
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


@router.post("/articles/{article_id}/unpublish", response_model=ArticlePublic)
def unpublish_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to unpublish")
    return unpublish_article(db, article)


@router.delete("/articles/{article_id}", status_code=204)
def delete_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to delete")
    delete_article(db, article)
    return None
