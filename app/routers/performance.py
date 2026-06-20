from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_project_member
from app.models.article import Article
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.performance import ArticlePerformance, ArticlePerformanceBrief, ProjectTrafficSummary
from app.services.performance_service import (
    get_all_articles_performance,
    get_article_performance,
    get_project_traffic_summary,
)

router = APIRouter(tags=["performance"])


@router.get("/projects/{project_id}/performance/summary", response_model=ProjectTrafficSummary)
def project_performance_summary(
    project_id: str,
    period: str = Query(default="30d", pattern=r"^(\d+d|today|yesterday)$"),
    db: Session = Depends(get_db),
    member: ProjectMember = Depends(get_project_member),
):
    return get_project_traffic_summary(db, project_id, period)


@router.get("/projects/{project_id}/performance/articles", response_model=list[ArticlePerformanceBrief])
def project_articles_performance(
    project_id: str,
    period: str = Query(default="30d", pattern=r"^(\d+d|today|yesterday)$"),
    db: Session = Depends(get_db),
    member: ProjectMember = Depends(get_project_member),
):
    return get_all_articles_performance(db, project_id, period)


@router.get("/articles/{article_id}/performance", response_model=ArticlePerformance)
def article_performance(
    article_id: str,
    period: str = Query(default="30d", pattern=r"^(\d+d|today|yesterday)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    from app.dependencies.auth import get_member_for_project
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Not a project member")

    return get_article_performance(db, article_id, period)
