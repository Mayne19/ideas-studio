from datetime import datetime, timezone
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.utils import calculate_word_count
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.article import Article, WRITER_EDITABLE_STATUSES
from app.models.seo_analysis import SeoAnalysis
from app.models.user import User
from app.schemas.editor import AutosaveRequest, AutosaveResponse, EditorData, AnalysisBrief, PreviewResponse
from app.services.callout_template_service import extract_callouts_from_content
from app.services.version_service import create_version, is_duplicate_autosave

router = APIRouter(tags=["editor"])

_ALL_WRITE_ROLES = frozenset({"owner", "admin", "editor", "writer"})
_EMPTY_CONTENT_MESSAGE = "Protection : contenu vide non sauvegardé pour éviter d'écraser un article existant."


def _is_effectively_empty_content(value: str | None) -> bool:
    if value is None:
        return True
    text = re.sub(r"<[^>]+>", " ", value)
    text = text.replace("&nbsp;", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text == ""


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


@router.get("/articles/{article_id}/editor", response_model=EditorData)
def get_editor_data(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = _get_article_or_404(db, article_id)
    _check_member(db, current_user.id, article.project_id)

    latest = (
        db.query(SeoAnalysis)
        .filter(SeoAnalysis.article_id == article_id)
        .order_by(SeoAnalysis.created_at.desc())
        .first()
    )
    analysis_brief = None
    if latest:
        analysis_brief = AnalysisBrief(
            seo_score=latest.seo_score,
            readability_score=latest.readability_score,
            quality_score=latest.quality_score,
            eeat_score=latest.eeat_score,
            readiness_status=latest.readiness_status,
            created_at=latest.created_at,
        )

    has_draft_changes = None
    if article.status == "published":
        has_draft_changes = (
            article.content != article.published_content
            or article.title != article.published_title
            or article.excerpt != article.published_excerpt
            or article.meta_description != article.published_meta_description
            or article.cover_image_url != article.published_cover_image_url
            or article.faq_json != article.published_faq_json
            or article.callouts_json != article.published_callouts_json
        )

    return EditorData(
        id=article.id,
        project_id=article.project_id,
        category_id=article.category_id,
        title=article.title,
        slug=article.slug,
        content=article.content,
        excerpt=article.excerpt,
        status=article.status,
        keyword=article.keyword,
        meta_title=article.meta_title,
        meta_description=article.meta_description,
        cover_image_url=article.cover_image_url,
        faq_json=article.faq_json,
        callouts_json=article.callouts_json,
        internal_links_json=article.internal_links_json,
        external_links_json=article.external_links_json,
        content_blocks_json=article.content_blocks_json,
        word_count=article.word_count,
        seo_score=article.seo_score,
        readability_score=article.readability_score,
        quality_score=article.quality_score,
        eeat_score=article.eeat_score,
        readiness_status=article.readiness_status,
        seo_review_json=article.seo_review_json,
        project_context_json=article.project_context_json,
        category_strategy_json=article.category_strategy_json,
        idea_discovery_json=article.idea_discovery_json,
        intent_analysis_json=article.intent_analysis_json,
        research_brief_json=article.research_brief_json,
        keyword_brief_json=article.keyword_brief_json,
        cannibalization_check_json=article.cannibalization_check_json,
        editorial_angle_json=article.editorial_angle_json,
        outline_json=article.outline_json,
        image_plan_json=article.image_plan_json,
        image_sources_json=article.image_sources_json,
        callout_plan_json=article.callout_plan_json,
        language_quality_report_json=article.language_quality_report_json,
        originality_report_json=article.originality_report_json,
        humanization_report_json=article.humanization_report_json,
        eeat_checklist_json=article.eeat_checklist_json,
        editorial_quality_report_json=article.editorial_quality_report_json,
        seo_final_checklist_json=article.seo_final_checklist_json,
        generation_report_json=article.generation_report_json,
        sources_json=article.sources_json,
        author_name=article.author_name,
        reading_time_minutes=article.reading_time_minutes,
        latest_analysis=analysis_brief,
        created_at=article.created_at,
        updated_at=article.updated_at,
        published_content=article.published_content,
        published_title=article.published_title,
        published_excerpt=article.published_excerpt,
        published_meta_description=article.published_meta_description,
        published_cover_image_url=article.published_cover_image_url,
        published_faq_json=article.published_faq_json,
        published_callouts_json=article.published_callouts_json,
        has_draft_changes=has_draft_changes,
    )


@router.post("/articles/{article_id}/autosave", response_model=AutosaveResponse)
def autosave_article(
    article_id: str,
    payload: AutosaveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    article = _get_article_or_404(db, article_id)
    member = _check_member(db, current_user.id, article.project_id)

    if member.role == "viewer":
        raise HTTPException(status_code=403, detail="Viewers cannot autosave")
    if member.role == "writer" and article.status not in WRITER_EDITABLE_STATUSES:
        raise HTTPException(status_code=403, detail="Writers can only edit draft articles")

    data = payload.model_dump(exclude_unset=True)

    # Never allow autosave to set published status
    data.pop("status", None)

    if (
        article.status == "published"
        and "content" in data
        and _is_effectively_empty_content(data.get("content"))
        and not _is_effectively_empty_content(article.content)
    ):
        raise HTTPException(status_code=409, detail=_EMPTY_CONTENT_MESSAGE)

    for field, value in data.items():
        setattr(article, field, value)

    if "content" in data:
        article.word_count = calculate_word_count(article.content)
        article.callouts_json = extract_callouts_from_content(article.content)

    version_created = False
    incoming_content = data.get("content", article.content)
    if not is_duplicate_autosave(db, article_id, incoming_content):
        create_version(db, article, "autosave", current_user.id)
        version_created = True

    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)

    return AutosaveResponse(
        id=article.id,
        word_count=article.word_count,
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

    return PreviewResponse(
        id=article.id,
        title=article.title,
        slug=article.slug,
        content=article.content,
        excerpt=article.excerpt,
        meta_title=article.meta_title,
        meta_description=article.meta_description,
        cover_image_url=article.cover_image_url,
        faq_json=article.faq_json,
        callouts_json=article.callouts_json,
        internal_links_json=article.internal_links_json,
        external_links_json=article.external_links_json,
        content_blocks_json=article.content_blocks_json,
        author_name=article.author_name,
        reading_time_minutes=article.reading_time_minutes,
        status=article.status,
    )
