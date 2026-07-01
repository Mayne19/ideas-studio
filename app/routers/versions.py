from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.utils import calculate_word_count
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.article import Article
from app.models.article_version import ArticleVersion
from app.models.user import User
from app.schemas.article import ArticlePublic
from app.schemas.editor import VersionPublic
from app.services.version_service import create_version

router = APIRouter(tags=["versions"])

_MANAGE_ROLES = frozenset({"owner", "admin", "editor"})


def _get_article_or_404(db: Session, article_id: str) -> Article:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


def _check_member(db: Session, user_id: str, project_id: str):
    member = get_member_for_project(db, user_id, project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    return member


@router.get("/articles/{article_id}/versions", response_model=list[VersionPublic])
def list_versions(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = _get_article_or_404(db, article_id)
    _check_member(db, current_user.id, article.project_id)

    versions = (
        db.query(ArticleVersion)
        .filter(ArticleVersion.article_id == article_id)
        .order_by(ArticleVersion.version_number.desc())
        .all()
    )
    return [
        VersionPublic(
            id=v.id,
            article_id=v.article_id,
            project_id=v.project_id,
            title=v.title,
            slug=v.slug,
            version_number=v.version_number,
            version_type=v.version_type,
            created_by=v.created_by,
            created_at=v.created_at,
        )
        for v in versions
    ]


@router.post("/articles/{article_id}/versions/{version_id}/restore", response_model=ArticlePublic)
def restore_version(
    article_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = _get_article_or_404(db, article_id)
    member = _check_member(db, current_user.id, article.project_id)

    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot restore versions")
    if member.role == "designer":
        raise HTTPException(status_code=403, detail="Designers cannot restore versions")

    version = (
        db.query(ArticleVersion)
        .filter(
            ArticleVersion.id == version_id,
            ArticleVersion.article_id == article_id,
        )
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Save current state before restoring
    create_version(db, article, "restore", current_user.id)

    # Apply version content
    article.title = version.title
    article.slug = version.slug
    article.content = version.content
    article.excerpt = version.excerpt
    article.meta_title = version.meta_title
    article.meta_description = version.meta_description
    article.cover_image_url = version.cover_image_url
    article.faq_json = version.faq_json
    article.callouts_json = version.callouts_json
    article.internal_links_json = version.internal_links_json
    article.external_links_json = version.external_links_json
    article.content_blocks_json = version.content_blocks_json
    article.word_count = calculate_word_count(version.content)
    article.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(article)
    return article
