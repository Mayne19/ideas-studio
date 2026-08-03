from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.content import Article, ArticleRevision
from app.models.reference import RevisionSource
from app.models.core import User
from app.schemas.article import ArticlePublic
from app.schemas.editor import VersionPublic
from app.services.article_service import to_public

router = APIRouter(tags=["versions"])

_MANAGE_ROLES = frozenset({"owner", "admin", "editor"})


def _get_article_or_404(db: Session, article_id: str) -> Article:
    article = db.get(Article, article_id)
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

    revisions = db.execute(
        select(ArticleRevision)
        .where(ArticleRevision.article_id == article_id)
        .order_by(ArticleRevision.revision_no.desc())
    ).scalars().all()
    return [
        VersionPublic(
            id=r.id,
            article_id=r.article_id,
            project_id=article.project_id,
            title=r.title,
            revision_no=r.revision_no,
            source=r.source,
            created_by=r.created_by,
            created_at=r.created_at,
        )
        for r in revisions
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

    if member.role in ("viewer", "designer"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to restore versions")

    target = db.execute(
        select(ArticleRevision).where(
            ArticleRevision.id == version_id,
            ArticleRevision.article_id == article_id,
        )
    ).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")

    last_no = db.execute(
        select(ArticleRevision.revision_no)
        .where(ArticleRevision.article_id == article.id)
        .order_by(ArticleRevision.revision_no.desc())
        .limit(1)
    ).scalar_one_or_none() or 0

    restored = ArticleRevision(
        article_id=article.id,
        revision_no=last_no + 1,
        source=RevisionSource.ROLLBACK,
        title=target.title,
        excerpt=target.excerpt,
        body=target.body,
        blocks=target.blocks,
        faq=target.faq,
        callouts=target.callouts,
        word_count=target.word_count,
        reading_time_minutes=target.reading_time_minutes,
        created_by=current_user.id,
    )
    db.add(restored)
    db.flush()
    article.current_revision_id = restored.id
    article.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(article)
    return to_public(db, article)
