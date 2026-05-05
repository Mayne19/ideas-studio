from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member
from app.models.optimization_recommendation import OptimizationRecommendation
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.recommendation import RecommendationPublic
from app.services.optimization_engine import review_published_articles

router = APIRouter(tags=["recommendations"])


def _get_rec_or_404(db: Session, recommendation_id: str) -> OptimizationRecommendation:
    rec = db.query(OptimizationRecommendation).filter(
        OptimizationRecommendation.id == recommendation_id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


def _check_member(db: Session, user_id: str, project_id: str) -> ProjectMember:
    from app.dependencies.auth import get_member_for_project
    member = get_member_for_project(db, user_id, project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")
    return member


@router.get("/projects/{project_id}/recommendations", response_model=list[RecommendationPublic])
def list_recommendations(
    project_id: str,
    db: Session = Depends(get_db),
    member: ProjectMember = Depends(get_project_member),
):
    return (
        db.query(OptimizationRecommendation)
        .filter(OptimizationRecommendation.project_id == project_id)
        .order_by(
            OptimizationRecommendation.priority.desc(),
            OptimizationRecommendation.created_at.desc(),
        )
        .all()
    )


@router.post("/projects/{project_id}/recommendations/review", response_model=dict)
def trigger_review(
    project_id: str,
    db: Session = Depends(get_db),
    member: ProjectMember = Depends(get_project_member),
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

    if rec.status not in {"pending"}:
        raise HTTPException(status_code=400, detail=f"Cannot accept a recommendation with status '{rec.status}'")

    rec.status = "accepted"
    rec.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/recommendations/{recommendation_id}/reject", response_model=RecommendationPublic)
def reject_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = _get_rec_or_404(db, recommendation_id)
    _check_member(db, current_user.id, rec.project_id)

    if rec.status not in {"pending", "accepted"}:
        raise HTTPException(status_code=400, detail=f"Cannot reject a recommendation with status '{rec.status}'")

    rec.status = "rejected"
    rec.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return rec


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

    rec.status = "applied"
    rec.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(rec)
    return rec
