from datetime import datetime, timezone
import logging
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.utils import calculate_word_count, calculate_reading_time_minutes
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.content import Article, ArticleRevision, ArticleScore, ArticleSeo
from app.models.reference import RevisionSource
from app.models.core import User
from app.schemas.editor import AutosaveRequest, AutosaveResponse, EditorData, AnalysisBrief, PreviewResponse
from app.services.article_service import primary_keyword, set_primary_keyword
from app.services.callout_template_service import extract_callouts_from_content
from app.services.seo.artifacts import get_all_latest_artifacts

logger = logging.getLogger(__name__)

router = APIRouter(tags=["editor"])

_ALL_WRITE_ROLES = frozenset({"owner", "admin", "editor", "designer"})
_EMPTY_CONTENT_MESSAGE = "Protection : contenu vide non sauvegardé pour éviter d'écraser un article existant."


def _is_effectively_empty_content(value: str | None) -> bool:
    if value is None:
        return True
    text = re.sub(r"<[^>]+>", " ", value)
    text = text.replace("&nbsp;", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text == ""


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


@router.get("/articles/{article_id}/editor", response_model=EditorData)
def get_editor_data(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = _get_article_or_404(db, article_id)
    _check_member(db, current_user.id, article.project_id)

    revision = article.current_revision
    published = article.published_revision
    seo = db.get(ArticleSeo, article.id)
    keyword = primary_keyword(db, article.id)

    latest_score = db.execute(
        select(ArticleScore)
        .where(ArticleScore.article_id == article.id)
        .order_by(ArticleScore.evaluated_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    analysis_brief = None
    if latest_score:
        analysis_brief = AnalysisBrief(
            seo_score=float(latest_score.seo_score) if latest_score.seo_score is not None else None,
            readability_score=float(latest_score.readability_score) if latest_score.readability_score is not None else None,
            quality_score=float(latest_score.quality_score) if latest_score.quality_score is not None else None,
            eeat_score=float(latest_score.eeat_score) if latest_score.eeat_score is not None else None,
            geo_score=float(latest_score.geo_score) if latest_score.geo_score is not None else None,
            global_score=float(latest_score.global_score) if latest_score.global_score is not None else None,
            created_at=latest_score.evaluated_at,
        )

    return EditorData(
        id=article.id,
        project_id=article.project_id,
        category_id=article.category_id,
        sub_niche=article.sub_niche,
        title=revision.title if revision else "",
        slug=article.slug,
        content=revision.body if revision else None,
        excerpt=revision.excerpt if revision else None,
        status=article.status_reason_id,
        keyword=keyword,
        meta_title=seo.meta_title if seo else None,
        meta_description=seo.meta_description if seo else None,
        faq=revision.faq if revision else [],
        callouts=revision.callouts if revision else [],
        word_count=revision.word_count if revision else 0,
        artifacts=get_all_latest_artifacts(db, article.id),
        author_name=article.author_name,
        reading_time_minutes=revision.reading_time_minutes if revision else None,
        is_featured=article.is_featured,
        latest_analysis=analysis_brief,
        created_at=article.created_at,
        updated_at=article.updated_at,
        published_title=published.title if published else None,
        published_content=published.body if published else None,
        published_excerpt=published.excerpt if published else None,
        published_meta_description=seo.meta_description if seo else None,
        has_draft_changes=article.current_revision_id != article.published_revision_id,
    )


@router.post("/articles/{article_id}/autosave", response_model=AutosaveResponse)
def autosave_article(
    article_id: str,
    payload: AutosaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.reference import ArticleStatus

    article = _get_article_or_404(db, article_id)
    member = _check_member(db, current_user.id, article.project_id)

    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot autosave")

    data = payload.model_dump(exclude_unset=True)
    current = article.current_revision

    if (
        article.status_reason_id == ArticleStatus.PUBLISHED
        and "content" in data
        and _is_effectively_empty_content(data.get("content"))
        and current
        and not _is_effectively_empty_content(current.body)
    ):
        raise HTTPException(status_code=409, detail=_EMPTY_CONTENT_MESSAGE)

    incoming_content = data.get("content", current.body if current else None)
    is_duplicate = current is not None and current.body == incoming_content and not (
        {"title", "excerpt", "faq", "callouts", "meta_title", "meta_description"} & data.keys()
    )

    version_created = False
    word_count = current.word_count if current else 0

    if not is_duplicate:
        last_no = db.execute(
            select(ArticleRevision.revision_no)
            .where(ArticleRevision.article_id == article.id)
            .order_by(ArticleRevision.revision_no.desc())
            .limit(1)
        ).scalar_one_or_none() or 0

        callouts = data.get("callouts")
        if callouts is None and "content" in data:
            callouts = extract_callouts_from_content(incoming_content) or (current.callouts if current else [])
        elif callouts is None:
            callouts = current.callouts if current else []

        word_count = calculate_word_count(incoming_content or "")
        revision = ArticleRevision(
            article_id=article.id,
            revision_no=last_no + 1,
            source=RevisionSource.HUMAN,
            title=data.get("title", current.title if current else ""),
            excerpt=data.get("excerpt", current.excerpt if current else None),
            body=incoming_content,
            faq=data.get("faq", current.faq if current else []),
            callouts=callouts,
            word_count=word_count,
            reading_time_minutes=calculate_reading_time_minutes(word_count),
            created_by=current_user.id,
        )
        db.add(revision)
        db.flush()
        article.current_revision_id = revision.id
        version_created = True

    if "meta_title" in data or "meta_description" in data:
        seo = db.get(ArticleSeo, article.id)
        if seo is None:
            seo = ArticleSeo(article_id=article.id)
            db.add(seo)
        if "meta_title" in data:
            seo.meta_title = data["meta_title"]
        if "meta_description" in data:
            seo.meta_description = data["meta_description"]

    if "keyword" in data:
        set_primary_keyword(db, article.project_id, article.id, data["keyword"])

    for field in ("category_id", "sub_niche", "author_name", "is_featured", "slug"):
        if field in data:
            setattr(article, field, data[field])

    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)

    try:
        from app.services.scoring_service import compute_global_score
        scoring = compute_global_score(db, article.id, article=article)
        db.add(ArticleScore(
            article_id=article.id,
            revision_id=article.current_revision_id,
            global_score=scoring.get("global_score"),
            seo_score=scoring.get("seo_contrib"),
            eeat_score=scoring.get("eeat_contrib"),
            readability_score=scoring.get("readability_contrib"),
            geo_score=scoring.get("geo_contrib"),
        ))
        db.commit()
    except Exception as exc:
        logger.error("Autosave scoring failed: %s", exc)
        db.rollback()

    return AutosaveResponse(
        id=article.id,
        word_count=word_count,
        updated=True,
        version_created=version_created,
        updated_at=article.updated_at,
    )


@router.get("/articles/{article_id}/preview", response_model=PreviewResponse)
def preview_article(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = _get_article_or_404(db, article_id)
    _check_member(db, current_user.id, article.project_id)
    revision = article.current_revision
    seo = db.get(ArticleSeo, article.id)

    return PreviewResponse(
        id=article.id,
        title=revision.title if revision else "",
        slug=article.slug,
        content=revision.body if revision else None,
        excerpt=revision.excerpt if revision else None,
        meta_title=seo.meta_title if seo else None,
        meta_description=seo.meta_description if seo else None,
        sub_niche=article.sub_niche,
        is_featured=article.is_featured,
        faq=revision.faq if revision else [],
        callouts=revision.callouts if revision else [],
        author_name=article.author_name,
        reading_time_minutes=revision.reading_time_minutes if revision else None,
        status=article.status_reason_id,
    )
