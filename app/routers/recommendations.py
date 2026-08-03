from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import MemberView, get_current_user, get_project_member
from app.models.content import Article
from app.models.analytics import OptimizationRecommendation
from app.models.ops import Notification
from app.models.core import User
from app.schemas.recommendation import RecommendationPublic
from app.services.optimization_engine import review_published_articles, set_recommendation_status, status_code, to_public

router = APIRouter(tags=["recommendations"])


def _get_rec_or_404(db: Session, recommendation_id: str) -> OptimizationRecommendation:
    rec = db.get(OptimizationRecommendation, recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


def _check_member(db: Session, user_id: str, project_id: str) -> MemberView:
    from app.dependencies.auth import get_member_for_project
    member = get_member_for_project(db, user_id, project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")
    return member


def _delete_optimization_notifications(db: Session, rec: OptimizationRecommendation) -> None:
    if not rec.article_id:
        return

    query = select(Notification).where(
        Notification.project_id == rec.project_id,
        Notification.type == "optimization",
    )

    article = db.get(Article, rec.article_id)
    revision = article.current_revision if article else None
    title = revision.title if revision else None
    article_link = f"/projects/{rec.project_id}/articles/{rec.article_id}/edit"
    filters = [Notification.link == article_link]
    if title:
        filters.append(Notification.title.ilike(f"%{title[:60]}%"))
    query = query.where(or_(*filters))

    for notification in db.execute(query).scalars().all():
        db.delete(notification)


@router.get("/projects/{project_id}/recommendations", response_model=list[RecommendationPublic])
def list_recommendations(
    project_id: str,
    db: Session = Depends(get_db),
    member: MemberView = Depends(get_project_member),
):
    recs = db.execute(
        select(OptimizationRecommendation)
        .where(OptimizationRecommendation.project_id == project_id)
        .order_by(
            OptimizationRecommendation.priority.desc(),
            OptimizationRecommendation.created_at.desc(),
        )
    ).scalars().all()
    return [to_public(r) for r in recs]


@router.post("/projects/{project_id}/recommendations/review", response_model=dict)
def trigger_review(
    project_id: str,
    db: Session = Depends(get_db),
    member: MemberView = Depends(get_project_member),
):
    if member.role not in {"owner", "admin", "editor"}:
        raise HTTPException(status_code=403, detail="Insufficient role")
    result = review_published_articles(db, project_id)
    db.commit()
    return result


@router.post("/recommendations/{recommendation_id}/accept", response_model=RecommendationPublic)
def accept_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = _get_rec_or_404(db, recommendation_id)
    _check_member(db, current_user.id, rec.project_id)

    if status_code(rec.status_reason_id) != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot accept a recommendation with status '{status_code(rec.status_reason_id)}'")

    set_recommendation_status(rec, "accepted")
    db.commit()
    db.refresh(rec)
    return to_public(rec)


@router.post("/recommendations/{recommendation_id}/reject", response_model=RecommendationPublic)
def reject_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = _get_rec_or_404(db, recommendation_id)
    _check_member(db, current_user.id, rec.project_id)

    if status_code(rec.status_reason_id) not in {"pending", "accepted"}:
        raise HTTPException(status_code=400, detail=f"Cannot reject a recommendation with status '{status_code(rec.status_reason_id)}'")

    set_recommendation_status(rec, "rejected")
    rec.resolved_at = datetime.now(timezone.utc)
    _delete_optimization_notifications(db, rec)
    db.commit()
    db.refresh(rec)
    return to_public(rec)


@router.post("/recommendations/{recommendation_id}/apply", response_model=RecommendationPublic)
def apply_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = _get_rec_or_404(db, recommendation_id)
    member = _check_member(db, current_user.id, rec.project_id)

    if member.role not in {"owner", "admin", "editor"}:
        raise HTTPException(status_code=403, detail="Insufficient role")

    set_recommendation_status(rec, "applied")
    rec.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return to_public(rec)
