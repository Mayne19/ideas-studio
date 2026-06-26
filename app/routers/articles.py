import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member, require_project_role, get_member_for_project
from app.models.user import User
from app.models.project_member import ProjectMember
from app.models.article import Article, WRITER_EDITABLE_STATUSES
from app.models.project import Project
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticlePublic, ArticleScheduleRequest, PromoteResponse, BulkValidateRequest, BulkValidateResponse

logger = logging.getLogger(__name__)
from app.services.article_service import (
    create_article,
    delete_article,
    get_article_by_id,
    list_articles,
    update_article,
    publish_article,
    promote_article,
    rollback_article,
    schedule_article,
    unpublish_article,
)
from app.services.seo.seo_review_service import (
    build_review_error_report,
    run_and_store_seo_review,
)
from app.services.publication_revalidation_service import trigger_project_revalidation

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
    archived: bool = False,
    blocked_cost_limit: Optional[float] = None,
    skip: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    effective_offset = skip if skip is not None else offset
    return list_articles(db, project_id, status=status, category_id=category_id, search=search,
                         published_only=published_only, archived=archived,
                         blocked_cost_limit=blocked_cost_limit,
                         limit=limit, offset=effective_offset)


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


@router.post("/projects/{project_id}/articles/{article_id}/seo-expert-review")
def seo_expert_review_route(
    project_id: str,
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article or article.project_id != project_id:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot run SEO expert review")

    try:
        review = run_and_store_seo_review(article)
    except Exception as exc:
        review = build_review_error_report(f"L'audit SEO Expert a echoue: {exc}")
        article.seo_review_json = review
        logger.warning("SEO expert review failed for article %s: %s", article.id, exc)

    db.commit()
    db.refresh(article)
    return review


@router.post("/articles/{article_id}/promote", response_model=PromoteResponse)
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
    article = promote_article(db, article)

    project = db.query(Project).filter(Project.id == article.project_id).first()
    revalidation = trigger_project_revalidation(db, project, article=article, event_type="article.updated") if project else {"revalidated": False}
    revalidated = bool(revalidation.get("revalidated"))

    return PromoteResponse(
        id=article.id,
        project_id=article.project_id,
        category_id=article.category_id,
        title=article.title,
        slug=article.slug,
        content=article.content,
        excerpt=article.excerpt,
        status=article.status,
        keyword=article.keyword,
        meta_title=article.meta_title,
        meta_description=article.meta_description,
        cover_image_url=article.cover_image_url,
        word_count=article.word_count,
        priority=article.priority,
        seo_score=article.seo_score,
        readability_score=article.readability_score,
        quality_score=article.quality_score,
        eeat_score=article.eeat_score,
        readiness_status=article.readiness_status,
        published_at=article.published_at,
        scheduled_at=article.scheduled_at,
        created_at=article.created_at,
        author_name=article.author_name,
        reading_time_minutes=article.reading_time_minutes,
        updated_at=article.updated_at,
        revalidated=revalidated,
    )


@router.post("/articles/{article_id}/publish", response_model=PromoteResponse)
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

    article = publish_article(db, article)

    project = db.query(Project).filter(Project.id == article.project_id).first()
    revalidation = trigger_project_revalidation(db, project, article=article, event_type="article.published") if project else {"revalidated": False}
    revalidated = bool(revalidation.get("revalidated"))

    return PromoteResponse(
        id=article.id,
        project_id=article.project_id,
        category_id=article.category_id,
        title=article.title,
        slug=article.slug,
        content=article.content,
        excerpt=article.excerpt,
        status=article.status,
        keyword=article.keyword,
        meta_title=article.meta_title,
        meta_description=article.meta_description,
        cover_image_url=article.cover_image_url,
        word_count=article.word_count,
        priority=article.priority,
        seo_score=article.seo_score,
        readability_score=article.readability_score,
        quality_score=article.quality_score,
        eeat_score=article.eeat_score,
        readiness_status=article.readiness_status,
        global_score=article.global_score,
        global_score_valid=bool(article.global_score_valid) if article.global_score_valid is not None else None,
        published_at=article.published_at,
        scheduled_at=article.scheduled_at,
        created_at=article.created_at,
        author_name=article.author_name,
        reading_time_minutes=article.reading_time_minutes,
        updated_at=article.updated_at,
        revalidated=revalidated,
    )


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

    # Compute and store global score
    from app.services.scoring_service import compute_global_score
    scoring = compute_global_score(article)
    article.global_score = scoring["global_score"]
    article.global_score_valid = 1 if scoring["global_score_valid"] else 0
    from datetime import datetime, timezone
    article.human_validated_at = datetime.now(timezone.utc)

    article.status = "ready_to_publish"
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


@router.post("/articles/{article_id}/unarchive", response_model=ArticlePublic)
def unarchive_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to restore")
    if article.status != "archived":
        raise HTTPException(status_code=400, detail="Seuls les articles archivés peuvent être restaurés.")
    article.status = "draft"
    article.scheduled_at = None
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


@router.post("/articles/{article_id}/rollback", response_model=ArticlePublic)
def rollback_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to rollback")
    if article.status != "published":
        raise HTTPException(status_code=400, detail="Seuls les articles publiés peuvent être restaurés.")
    return rollback_article(db, article)


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


@router.post("/projects/{project_id}/articles/bulk/validate", response_model=BulkValidateResponse)
def bulk_validate_articles_route(
    project_id: str,
    data: BulkValidateRequest,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    from app.services.validation_service import validate_bulk_articles
    return validate_bulk_articles(db, project_id, data.article_ids)


@router.post("/projects/{project_id}/articles/bulk/publish", response_model=BulkValidateResponse)
def bulk_publish_articles_route(
    project_id: str,
    data: BulkValidateRequest,
    member: ProjectMember = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    articles = db.query(Article).filter(
        Article.id.in_(data.article_ids),
        Article.project_id == project_id,
    ).all()

    found_ids = {article.id for article in articles}
    not_found = [article_id for article_id in data.article_ids if article_id not in found_ids]

    project = db.query(Project).filter(Project.id == project_id).first()
    published_count = 0
    for article in articles:
        published = publish_article(db, article)
        published_count += 1
        if project:
            trigger_project_revalidation(db, project, article=published, event_type="article.published")

    return {
        "validated_count": published_count,
        "scheduled_count": published_count,
        "blocked_count": 0,
        "not_found_count": len(not_found),
        "not_found_ids": not_found,
        "blocked_articles": [],
    }


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
