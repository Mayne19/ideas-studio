from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.user import User
from app.models.article import Article
from app.models.article_comment import ArticleComment
from app.schemas.comment import CommentCreate, CommentUpdate, CommentPublic
from datetime import datetime, timezone

router = APIRouter(tags=["comments"])

_MANAGE_ROLES = ("owner", "admin", "editor")


@router.get("/articles/{article_id}/comments", response_model=list[CommentPublic])
def list_comments(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    comments = (
        db.query(ArticleComment)
        .filter(ArticleComment.article_id == article_id)
        .order_by(ArticleComment.created_at.desc())
        .all()
    )
    return comments


@router.post("/articles/{article_id}/comments", response_model=CommentPublic, status_code=201)
def create_comment(
    article_id: str,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")
    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot comment")

    comment = ArticleComment(
        article_id=article_id,
        project_id=article.project_id,
        author_id=current_user.id,
        author_name=current_user.name or current_user.email,
        text=data.text,
        selected_text=data.selected_text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.patch("/articles/{article_id}/comments/{comment_id}", response_model=CommentPublic)
def update_comment(
    article_id: str,
    comment_id: str,
    data: CommentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.query(ArticleComment).filter(
        ArticleComment.id == comment_id,
        ArticleComment.article_id == article_id,
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member:
        raise HTTPException(status_code=403, detail="Access denied")

    if data.resolved is not None:
        comment.resolved = data.resolved
        comment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/articles/{article_id}/comments/{comment_id}", status_code=204)
def delete_comment(
    article_id: str,
    comment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.query(ArticleComment).filter(
        ArticleComment.id == comment_id,
        ArticleComment.article_id == article_id,
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    member = get_member_for_project(db, current_user.id, article.project_id)
    if not member or member.role not in _MANAGE_ROLES:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    db.delete(comment)
    db.commit()
    return None
