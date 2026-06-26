from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.article import ArticlePublicApiResponse
from app.services.article_service import get_public_articles, get_public_article_by_slug
from app.services.category_service import get_categories_for_project
from app.schemas.category import CategoryPublic

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/projects/{project_id}/articles", response_model=list[ArticlePublicApiResponse])
def list_public_articles(
    project_id: str,
    response: Response,
    limit: int = 20,
    offset: int = 0,
    category_slug: str | None = None,
    sub_niche: str | None = None,
    featured: bool | None = None,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    return get_public_articles(
        db,
        project_id,
        limit=limit,
        offset=offset,
        category_slug=category_slug,
        sub_niche=sub_niche,
        featured=featured,
    )


@router.get("/projects/{project_id}/articles/{slug}", response_model=ArticlePublicApiResponse)
def get_public_article(
    project_id: str,
    slug: str,
    response: Response,
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    article = get_public_article_by_slug(db, project_id, slug)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found or not published")
    return article


@router.get("/projects/{project_id}/categories", response_model=list[CategoryPublic])
def list_public_categories(
    project_id: str,
    db: Session = Depends(get_db),
):
    return get_categories_for_project(db, project_id)
