from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.content import Article, ArticleScore
from app.models.core import ProjectMember, User
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
    member = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    ).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")
    from app.dependencies.auth import role_code
    if role_code(member.role_id) not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient role")
    return member


def _get_article_or_404(db: Session, article_id: str) -> Article:
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _analysis_to_response(analysis: dict) -> SeoAnalysisResponse:
    issues = [SeoIssueSchema(**i) for i in analysis["issues"]]
    return SeoAnalysisResponse(
        id=analysis["id"],
        article_id=analysis["article_id"],
        project_id=analysis["project_id"],
        seo_score=analysis["seo_score"],
        readability_score=analysis["readability_score"],
        quality_score=analysis["quality_score"],
        eeat_score=analysis["eeat_score"],
        readiness_status=analysis["readiness_status"],
        issues=issues,
        suggestions=analysis["suggestions"],
        created_at=analysis["created_at"],
    )


def _latest_score_response(db: Session, article_id: str, project_id: str) -> SeoAnalysisResponse:
    score = db.execute(
        select(ArticleScore)
        .where(ArticleScore.article_id == article_id)
        .order_by(ArticleScore.evaluated_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="No analysis found for this article")
    return SeoAnalysisResponse(
        id=score.id,
        article_id=article_id,
        project_id=project_id,
        seo_score=float(score.seo_score) if score.seo_score is not None else 0,
        readability_score=float(score.readability_score) if score.readability_score is not None else 0,
        quality_score=float(score.quality_score) if score.quality_score is not None else 0,
        eeat_score=float(score.eeat_score) if score.eeat_score is not None else 0,
        readiness_status=score.readiness_status or "unknown",
        issues=[SeoIssueSchema(**i) for i in (score.issues or [])],
        suggestions=score.suggestions or [],
        created_at=score.evaluated_at,
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
    return _analysis_to_response(analysis)


@router.get("/articles/{article_id}/analysis/latest", response_model=SeoAnalysisResponse)
def get_latest_analysis(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(db, article_id)
    _check_role(db, current_user.id, article.project_id, {"owner", "admin", "editor", "viewer"})
    return _latest_score_response(db, article_id, article.project_id)


@router.get("/articles/{article_id}/analyses", response_model=list[SeoAnalysisResponse])
def list_analyses(
    article_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = _get_article_or_404(db, article_id)
    _check_role(db, current_user.id, article.project_id, {"owner", "admin", "editor", "viewer"})

    scores = db.execute(
        select(ArticleScore)
        .where(ArticleScore.article_id == article_id)
        .order_by(ArticleScore.evaluated_at.desc())
    ).scalars().all()
    return [
        SeoAnalysisResponse(
            id=s.id,
            article_id=article_id,
            project_id=article.project_id,
            seo_score=float(s.seo_score) if s.seo_score is not None else 0,
            readability_score=float(s.readability_score) if s.readability_score is not None else 0,
            quality_score=float(s.quality_score) if s.quality_score is not None else 0,
            eeat_score=float(s.eeat_score) if s.eeat_score is not None else 0,
            readiness_status=s.readiness_status or "unknown",
            issues=[SeoIssueSchema(**i) for i in (s.issues or [])],
            suggestions=s.suggestions or [],
            created_at=s.evaluated_at,
        )
        for s in scores
    ]


@router.patch("/articles/{article_id}/editor", response_model=dict)
def editor_update(
    article_id: str,
    payload: ArticleEditorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Route historique redondante avec POST /articles/{id}/autosave (editor.py) —
    conservée pour compatibilité, déléguée à la même logique de révision."""
    from app.schemas.article import ArticleUpdate
    from app.services.article_service import update_article

    article = _get_article_or_404(db, article_id)
    _check_role(db, current_user.id, article.project_id, {"owner", "admin", "editor"})

    data = payload.model_dump(exclude_unset=True)
    update_data = ArticleUpdate(**{k: v for k, v in data.items() if k in ArticleUpdate.model_fields})
    article = update_article(db, article, update_data)
    revision = article.current_revision
    return {"id": article.id, "updated": True, "word_count": revision.word_count if revision else 0}


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

    all_issues = [SeoIssueSchema(**i) for i in analysis["issues"]]
    blocking = [i for i in all_issues if i.severity == "critical"]
    can_publish = len(blocking) == 0

    from app.services.scoring_service import compute_global_score
    from app.services.validation_service import check_validation_thresholds, compute_critical_warnings, _load_validation_context
    scoring = compute_global_score(db, article.id, article=article)
    ctx = _load_validation_context(db, article)
    warnings = compute_critical_warnings(ctx)
    validation = check_validation_thresholds(db, article)

    return ReadyCheckResponse(
        article_id=article_id,
        readiness_status=analysis["readiness_status"],
        seo_score=analysis["seo_score"],
        readability_score=analysis["readability_score"],
        quality_score=analysis["quality_score"],
        eeat_score=analysis["eeat_score"],
        global_score=scoring["global_score"],
        global_score_valid=scoring["global_score_valid"],
        blocking_issues=blocking,
        critical_warnings=[CriticalWarningSchema(**w) for w in warnings],
        can_publish=can_publish and validation["valid"],
    )
