from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.core import User
from app.models.content import Article, ArticleComment
from app.schemas.comment import CommentCreate, CommentUpdate, CommentPublic
from datetime import datetime, timezone

router = APIRouter(tags=["comments"])

_MANAGE_ROLES = ("owner", "admin", "editor")


def _user_display_name(user: User | None) -> str | None:
    if not user:
        return None
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email


def _to_public(db: Session, comment: ArticleComment) -> CommentPublic:
    author = db.get(User, comment.author_id) if comment.author_id else None
    return CommentPublic(
        id=comment.id,
        article_id=comment.article_id,
        author_id=comment.author_id,
        author_name=_user_display_name(author),
        parent_id=comment.parent_id,
        text=comment.body,
        selected_text=comment.quoted_text,
        resolved=comment.resolved_at is not None,
        created_at=comment.created_at,
    )


@router.get("/articles/{article_id}/comments", response_model=list[CommentPublic])
def list_comments(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    comments = db.execute(
        select(ArticleComment)
        .where(ArticleComment.article_id == article_id)
        .order_by(ArticleComment.created_at.desc())
    ).scalars().all()
    return [_to_public(db, c) for c in comments]


@router.post("/articles/{article_id}/comments", response_model=CommentPublic, status_code=201)
def create_comment(
    article_id: str,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot comment")

    comment = ArticleComment(
        article_id=article_id,
        author_id=current_user.id,
        parent_id=data.parent_id,
        body=data.text,
        quoted_text=data.selected_text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _to_public(db, comment)


@router.patch("/articles/{article_id}/comments/{comment_id}", response_model=CommentPublic)
def update_comment(
    article_id: str,
    comment_id: str,
    data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.execute(
        select(ArticleComment).where(
            ArticleComment.id == comment_id,
            ArticleComment.article_id == article_id,
        )
    ).scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role not in _MANAGE_ROLES and comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if data.resolved is not None:
        comment.resolved_at = datetime.now(timezone.utc) if data.resolved else None
    db.commit()
    db.refresh(comment)
    return _to_public(db, comment)


@router.delete("/articles/{article_id}/comments/{comment_id}", status_code=204)
def delete_comment(
    article_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.execute(
        select(ArticleComment).where(
            ArticleComment.id == comment_id,
            ArticleComment.article_id == article_id,
        )
    ).scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role not in _MANAGE_ROLES and comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    db.delete(comment)
    db.commit()
    return None
