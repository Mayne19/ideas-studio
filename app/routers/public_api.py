from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.article import ArticlePublicApiResponse
from app.services.article_service import get_public_articles, get_public_article_by_slug

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/projects/{project_id}/articles", response_model=list[ArticlePublicApiResponse])
def list_public_articles(
    project_id: str,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    return get_public_articles(db, project_id, limit=limit, offset=offset)


@router.get("/projects/{project_id}/articles/{slug}", response_model=ArticlePublicApiResponse)
def get_public_article(
    project_id: str,
    slug: str,
    db: Session = Depends(get_db),
):
    article = get_public_article_by_slug(db, project_id, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found or not published")
    return article
