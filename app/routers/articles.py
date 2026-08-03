import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import MemberView, get_current_user, get_project_member, require_project_role, get_member_for_project
from app.models.core import Project, User
from app.models.content import Article
from app.models.reference import ArticleStatus, set_article_status
from app.schemas.article import ArticleCreate, ArticleUpdate, ArticlePublic, ArticleScheduleRequest, PromoteResponse, BulkValidateRequest, BulkValidateResponse, BulkValidateByScoreRequest, BulkValidateByScoreResponse

logger = logging.getLogger(__name__)
from app.services.article_service import (
    create_article,
    delete_article,
    get_article_by_id,
    list_articles,
    promote_article,
    to_public,
    update_article,
)
from app.services.article_lifecycle_service import (
    publish_article,
    schedule_article_with_validation,
    unpublish_article,
    unschedule_article,
    rollback_article,
)
from app.services.seo.seo_review_service import (
    build_review_error_report,
    run_and_store_seo_review,
)
from app.services.publication_revalidation_service import trigger_project_revalidation

router = APIRouter(tags=["articles"])

_MANAGE_ROLES = ("owner", "admin", "editor")

# Statuts autorisés pour la publication en lot (exclut idées, publiés et archivés)
PUBLISHABLE_STATUSES = {
    ArticleStatus.DRAFT, ArticleStatus.DRAFT_READY, ArticleStatus.READY_TO_PUBLISH,
    ArticleStatus.SCHEDULED, ArticleStatus.REVIEW_NEEDED,
}
_ALL_WRITE_ROLES = ("owner", "admin", "editor", "designer")


@router.get("/projects/{project_id}/articles", response_model=list[ArticlePublic])
def list_articles_route(
    project_id: str,
    status: Optional[int] = None,
    statuses: Optional[str] = None,
    category_id: Optional[str] = None,
    search: Optional[str] = None,
    published_only: bool = False,
    archived: bool = False,
    blocked_cost_limit: Optional[float] = None,
    skip: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    effective_offset = skip if skip is not None else offset
    statuses_list = [int(s.strip()) for s in statuses.split(",") if s.strip()] if statuses else None
    articles = list_articles(db, project_id, status=status, statuses=statuses_list,
                         category_id=category_id, search=search,
                         published_only=published_only, archived=archived,
                         blocked_cost_limit=blocked_cost_limit,
                         limit=limit, offset=effective_offset)
    return [to_public(db, a) for a in articles]


@router.post("/projects/{project_id}/articles", response_model=ArticlePublic, status_code=201)
def create_article_route(
    project_id: str,
    data: ArticleCreate,
    member: MemberView = Depends(require_project_role(*_ALL_WRITE_ROLES)),
    db: Session = Depends(get_db),
):
    return to_public(db, create_article(db, data, project_id))


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
    return to_public(db, article)


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
    return to_public(db, update_article(db, article, data))


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
        review = run_and_store_seo_review(db, article)
    except Exception as exc:
        review = build_review_error_report(f"L'audit SEO Expert a echoue: {exc}")
        from app.services.seo.artifacts import save_artifact
        save_artifact(db, article.id, "seo_review", review)
        logger.warning("SEO expert review failed for article %s: %s", article.id, exc)

    db.commit()
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
    if article.status_reason_id != ArticleStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Only published articles can be promoted")
    article = promote_article(db, article)

    project = db.get(Project, article.project_id)
    revalidation = trigger_project_revalidation(db, project, article=article, event_type="article.updated") if project else {"revalidated": False}

    return to_public(db, article)


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

    project = db.get(Project, article.project_id)
    if project:
        trigger_project_revalidation(db, project, article=article, event_type="article.published")

    return to_public(db, article)


@router.post("/articles/{article_id}/unschedule", response_model=ArticlePublic)
def unschedule_article_route(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = get_article_by_id(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions to unschedule")
    if article.status_reason_id != ArticleStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail="Seuls les articles programmés peuvent être déprogrammés.")
    return to_public(db, unschedule_article(db, article))


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
    return to_public(db, schedule_article_with_validation(db, article, data.scheduled_at))


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
    if member.role in ("viewer", "designer"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to change article status")

    from app.services.scoring_service import compute_global_score
    from app.models.content import ArticleScore
    scoring = compute_global_score(db, article.id, article=article)
    db.add(ArticleScore(
        article_id=article.id,
        revision_id=article.current_revision_id,
        global_score=scoring["global_score"],
        seo_score=scoring["seo_contrib"],
        eeat_score=scoring["eeat_contrib"],
        readability_score=scoring["readability_contrib"],
        geo_score=scoring["geo_contrib"],
    ))

    set_article_status(article, ArticleStatus.READY_TO_PUBLISH)
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return to_public(db, article)


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
    set_article_status(article, ArticleStatus.ARCHIVED)
    article.archived_at = datetime.now(timezone.utc)
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return to_public(db, article)


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
    if article.status_reason_id != ArticleStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Seuls les articles archivés peuvent être restaurés.")
    set_article_status(article, ArticleStatus.DRAFT)
    article.archived_at = None
    article.scheduled_for = None
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return to_public(db, article)


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
    if article.status_reason_id != ArticleStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Seuls les articles publiés peuvent être restaurés.")
    return to_public(db, rollback_article(db, article))


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
    return to_public(db, unpublish_article(db, article))


@router.post("/projects/{project_id}/articles/bulk/validate", response_model=BulkValidateResponse)
def bulk_validate_articles_route(
    project_id: str,
    data: BulkValidateRequest,
    member: MemberView = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    from app.services.validation_service import validate_bulk_articles
    return validate_bulk_articles(db, project_id, data.article_ids)


@router.post("/projects/{project_id}/articles/bulk/validate-by-score", response_model=BulkValidateByScoreResponse)
def bulk_validate_by_score_route(
    project_id: str,
    data: BulkValidateByScoreRequest,
    member: MemberView = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    from app.services.validation_service import validate_bulk_articles
    from app.models.content import ArticleScore

    eligible_articles = db.execute(
        select(Article)
        .join(ArticleScore, ArticleScore.article_id == Article.id)
        .where(
            Article.project_id == project_id,
            Article.status_reason_id.in_(data.statuses),
            ArticleScore.global_score >= data.min_score,
        )
    ).scalars().unique().all()
    total_eligible = len(eligible_articles)
    eligible_ids = [a.id for a in eligible_articles]
    result = validate_bulk_articles(db, project_id, eligible_ids)
    return {
        **result,
        "score_threshold_applied": data.min_score,
        "total_eligible": total_eligible,
    }


@router.post("/projects/{project_id}/articles/bulk/publish", response_model=BulkValidateResponse)
def bulk_publish_articles_route(
    project_id: str,
    data: BulkValidateRequest,
    member: MemberView = Depends(require_project_role(*_MANAGE_ROLES)),
    db: Session = Depends(get_db),
):
    articles = db.execute(
        select(Article).where(Article.id.in_(data.article_ids), Article.project_id == project_id)
    ).scalars().all()

    found_ids = {article.id for article in articles}
    not_found = [article_id for article_id in data.article_ids if article_id not in found_ids]

    project = db.get(Project, project_id)
    published_count = 0
    blocked = []
    for article in articles:
        if article.status_reason_id not in PUBLISHABLE_STATUSES:
            blocked.append({
                "article_id": article.id,
                "title": article.current_revision.title if article.current_revision else "",
                "reasons": [f"Statut non publiable: {article.status_reason_id}"],
            })
            continue
        published = publish_article(db, article)
        published_count += 1
        if project:
            trigger_project_revalidation(db, project, article=published, event_type="article.published")

    return {
        "validated_count": published_count,
        "scheduled_count": published_count,
        "blocked_count": len(blocked),
        "not_found_count": len(not_found),
        "not_found_ids": not_found,
        "blocked_articles": blocked,
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
