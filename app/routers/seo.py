import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.article import Article
from app.models.project_member import ProjectMember
from app.models.seo_analysis import SeoAnalysis
from app.models.user import User
from app.schemas.seo import (
    ArticleEditorUpdate,
    CriticalWarningSchema,
    ReadyCheckResponse,
    SeoAnalysisResponse,
    SeoIssueSchema,
)
from app.services.seo_analyzer import analyze_article

router = APIRouter(tags=["seo"])


def _check_role(db: Session, user_id: str, project_id: str, allowed_roles: set) -> ProjectMember:
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")
    if member.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return member


def _get_article_or_404(db: Session, article_id: str) -> Article:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _analysis_to_response(analysis: SeoAnalysis) -> SeoAnalysisResponse:
    issues = [SeoIssueSchema(**i) for i in json.loads(analysis.issues_json)]
    suggestions = json.loads(analysis.suggestions_json)
    return SeoAnalysisResponse(
        id=analysis.id,
        article_id=analysis.article_id,
        project_id=analysis.project_id,
        seo_score=analysis.seo_score,
        readability_score=analysis.readability_score,
        quality_score=analysis.quality_score,
        eeat_score=analysis.eeat_score,
        readiness_status=analysis.readiness_status,
        issues=issues,
        suggestions=suggestions,
        created_at=analysis.created_at,
    )


@router.post("/articles/{article_id}/analyze", response_model=SeoAnalysisResponse)
def run_analysis(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(db, article_id)
    _check_role(db, current_user.id, article.project_id, {"owner", "admin", "editor"})

    analysis = analyze_article(db, article_id)
    db.commit()
    db.refresh(analysis)
    return _analysis_to_response(analysis)


@router.get("/articles/{article_id}/analysis/latest", response_model=SeoAnalysisResponse)
def get_latest_analysis(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(db, article_id)
    _check_role(db, current_user.id, article.project_id, {"owner", "admin", "editor", "viewer"})

    analysis = (
        db.query(SeoAnalysis)
        .filter(SeoAnalysis.article_id == article_id)
        .order_by(SeoAnalysis.created_at.desc())
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis found for this article")
    return _analysis_to_response(analysis)


@router.get("/articles/{article_id}/analyses", response_model=list[SeoAnalysisResponse])
def list_analyses(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(db, article_id)
    _check_role(db, current_user.id, article.project_id, {"owner", "admin", "editor", "viewer"})

    analyses = (
        db.query(SeoAnalysis)
        .filter(SeoAnalysis.article_id == article_id)
        .order_by(SeoAnalysis.created_at.desc())
        .all()
    )
    return [_analysis_to_response(a) for a in analyses]


@router.patch("/articles/{article_id}/editor", response_model=dict)
def editor_update(
    article_id: str,
    payload: ArticleEditorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    from app.core.utils import calculate_word_count
    from app.services.version_service import create_version, should_create_manual_version

    article = _get_article_or_404(db, article_id)
    _check_role(db, current_user.id, article.project_id, {"owner", "admin", "editor"})

    data = payload.model_dump(exclude_unset=True)

    if should_create_manual_version(data):
        create_version(db, article, "manual", current_user.id)

    for field, value in data.items():
        setattr(article, field, value)

    if "content" in data:
        article.word_count = calculate_word_count(article.content)

    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return {"id": article.id, "updated": True, "word_count": article.word_count}


@router.post("/articles/{article_id}/ready-check", response_model=ReadyCheckResponse)
def ready_check(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(db, article_id)
    _check_role(db, current_user.id, article.project_id, {"owner", "admin", "editor", "viewer"})

    analysis = analyze_article(db, article_id)
    db.commit()
    db.refresh(analysis)

    all_issues = [SeoIssueSchema(**i) for i in json.loads(analysis.issues_json)]
    blocking = [i for i in all_issues if i.severity == "critical"]
    can_publish = len(blocking) == 0

    from app.services.scoring_service import compute_global_score
    from app.services.validation_service import check_validation_thresholds, compute_critical_warnings
    scoring = compute_global_score(article)
    warnings = compute_critical_warnings(article)
    validation = check_validation_thresholds(article)

    return ReadyCheckResponse(
        article_id=article_id,
        readiness_status=analysis.readiness_status,
        seo_score=analysis.seo_score,
        readability_score=analysis.readability_score,
        quality_score=analysis.quality_score,
        eeat_score=analysis.eeat_score,
        global_score=scoring["global_score"],
        global_score_valid=scoring["global_score_valid"],
        blocking_issues=blocking,
        critical_warnings=[CriticalWarningSchema(**w) for w in warnings],
        can_publish=can_publish and validation["valid"],
    )
