import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_project_role, role_code
from app.models.core import User
from app.models.content import Article
from app.models.reference import MembershipStatus
from app.services.monitoring_agent import (
    analyze_article_for_improvement,
    scan_for_review,
    create_improvement_draft,
)
from app.services.seo.artifacts import get_latest_artifact

logger = logging.getLogger(__name__)

router = APIRouter(tags=["monitoring"])


def _get_article_or_404(article_id: str, db: Session) -> Article:
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _check_role(db: Session, user_id: str, project_id: str, allowed_roles: tuple) -> None:
    from app.models.core import ProjectMember
    member = db.execute(
        select(ProjectMember).where(
            ProjectMember.user_id == user_id,
            ProjectMember.project_id == project_id,
            ProjectMember.status_reason_id == MembershipStatus.ACTIVE,
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Access denied: not a project member")
    if role_code(member.role_id) not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Required role(s): {', '.join(allowed_roles)}")


@router.post("/articles/{article_id}/analyze-improvement")
def analyze_improvement_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze a published article and propose improvements."""
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))

    result = analyze_article_for_improvement(db, article_id)
    if not result:
        raise HTTPException(status_code=400, detail="Article is not published or cannot be analyzed")

    db.commit()
    db.refresh(result)
    return {
        "id": result.id,
        "status": result.status_reason_id,
        "performance_diagnosis": get_latest_artifact(db, article_id, "performance_diagnosis"),
        "improvement_proposal": get_latest_artifact(db, article_id, "improvement_proposal"),
    }


@router.post("/articles/{article_id}/create-improvement-draft")
def create_improvement_draft_route(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an improvement draft from a monitoring proposal."""
    article = _get_article_or_404(article_id, db)
    _check_role(db, current_user.id, article.project_id, ("owner", "admin", "editor"))

    draft = create_improvement_draft(db, article_id)
    if not draft:
        raise HTTPException(status_code=400, detail="Cannot create improvement draft (no proposal or already in progress)")

    db.commit()
    db.refresh(article)
    return {
        "id": draft.id,
        "title": draft.title,
        "article_id": article.id,
        "status": article.status_reason_id,
    }


@router.post("/projects/{project_id}/monitoring/scan")
def scan_monitoring_route(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member=Depends(require_project_role("owner", "admin")),
):
    """Scan all published articles and create improvement proposals where needed."""
    reviewed = scan_for_review(db, project_id=project_id)
    return {
        "scanned": len(reviewed),
        "articles_with_proposals": [
            {"id": a.id, "title": a.current_revision.title if a.current_revision else "", "status": a.status_reason_id}
            for a in reviewed
        ],
    }
