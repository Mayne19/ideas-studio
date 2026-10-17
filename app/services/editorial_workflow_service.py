"""Parcours éditorial parallèle au pipeline historique.

Ce module expose les états métier attendus par le nouveau parcours sans
modifier les identifiants de statut déjà présents en base. L'ancien pipeline
reste donc utilisable pendant les phases 1 et 2.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from enum import StrEnum

import markdown
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.ai import Artifact, Pipeline
from app.models.content import Article, ArticleRevision, ArticleSeo, Category
from app.models.reference import ArticleStatus, RevisionSource, set_article_status
from app.core.utils import generate_unique_slug, slugify
from app.services.article_service import primary_keyword, set_primary_keyword
from app.services.seo.artifacts import get_latest_artifact, save_artifact
from app.services.editorial_score_service import compute_editorial_score, store_editorial_score
from app.services.pipeline_service import resolve_min_publish_score


WORKFLOW_ARTIFACT_KEY = "editorial_workflow"
FICHE_ARTIFACT_KEY = "editorial_fiche"


class EditorialStatus(StrEnum):
    IDEA = "idea"
    WRITING = "writing"
    REVIEW = "review"
    VALIDATED = "validated"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    UPDATE = "update"
    ERROR = "error"


ARTICLE_STATUS_BY_WORKFLOW_STATUS: dict[EditorialStatus, ArticleStatus] = {
    EditorialStatus.IDEA: ArticleStatus.IDEA_PROPOSED,
    EditorialStatus.WRITING: ArticleStatus.WRITING_IN_PROGRESS,
    EditorialStatus.REVIEW: ArticleStatus.REVIEW_NEEDED,
    EditorialStatus.VALIDATED: ArticleStatus.READY_TO_PUBLISH,
    EditorialStatus.SCHEDULED: ArticleStatus.SCHEDULED,
    EditorialStatus.PUBLISHED: ArticleStatus.PUBLISHED,
    EditorialStatus.UPDATE: ArticleStatus.UPDATE_RECOMMENDED,
}

WORKFLOW_STATUS_BY_ARTICLE_STATUS: dict[ArticleStatus, EditorialStatus] = {
    ArticleStatus.DRAFT: EditorialStatus.IDEA,
    ArticleStatus.IDEA_PROPOSED: EditorialStatus.IDEA,
    ArticleStatus.IDEA_PRIORITY: EditorialStatus.IDEA,
    ArticleStatus.OUTLINE_READY: EditorialStatus.WRITING,
    ArticleStatus.WRITING_REQUESTED: EditorialStatus.WRITING,
    ArticleStatus.WRITING_IN_PROGRESS: EditorialStatus.WRITING,
    ArticleStatus.DRAFT_READY: EditorialStatus.REVIEW,
    ArticleStatus.REVIEW_NEEDED: EditorialStatus.REVIEW,
    ArticleStatus.CORRECTION_NEEDED: EditorialStatus.REVIEW,
    ArticleStatus.READY_TO_PUBLISH: EditorialStatus.VALIDATED,
    ArticleStatus.SCHEDULED: EditorialStatus.SCHEDULED,
    ArticleStatus.PUBLISHED: EditorialStatus.PUBLISHED,
    ArticleStatus.UNPUBLISHED: EditorialStatus.UPDATE,
    ArticleStatus.UPDATE_RECOMMENDED: EditorialStatus.UPDATE,
    ArticleStatus.IMPROVEMENT_PROPOSED: EditorialStatus.UPDATE,
    ArticleStatus.IMPROVEMENT_IN_PROGRESS: EditorialStatus.UPDATE,
    ArticleStatus.IMPROVEMENT_READY: EditorialStatus.UPDATE,
    ArticleStatus.FAILED: EditorialStatus.ERROR,
    ArticleStatus.BLOCKED_COST_LIMIT: EditorialStatus.ERROR,
}


def workflow_status(article: Article) -> EditorialStatus | None:
    """Convert an existing database status to one of the seven public states."""
    return WORKFLOW_STATUS_BY_ARTICLE_STATUS.get(ArticleStatus(article.status_reason_id))


def _latest_revision(db: Session, article_id: str) -> ArticleRevision | None:
    return db.execute(
        select(ArticleRevision)
        .where(ArticleRevision.article_id == article_id)
        .order_by(desc(ArticleRevision.revision_no))
        .limit(1)
    ).scalar_one_or_none()


def _next_revision_no(db: Session, article_id: str) -> int:
    revision = _latest_revision(db, article_id)
    return (revision.revision_no if revision else 0) + 1


def _markdown_to_html(source: str) -> str:
    return markdown.markdown(source, extensions=["tables", "sane_lists"])


def _unique_slug(db: Session, project_id: str, title: str) -> str:
    base = slugify(title) or f"idee-{uuid.uuid4().hex[:8]}"
    existing = set(
        db.execute(
            select(Article.slug).where(
                Article.project_id == project_id,
                Article.slug.like(f"{base}%"),
            )
        ).scalars().all()
    )
    return generate_unique_slug(base, existing)


def create_workflow_idea(
    db: Session,
    project_id: str,
    title: str,
    *,
    keyword: str | None = None,
    category_id: str | None = None,
    search_intent: str | None = None,
    context_hint: str | None = None,
    audience: str | None = None,
    angle: str | None = None,
) -> Article:
    """Create a subject for the local writer without calling an AI provider."""
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("Le sujet ou le titre est obligatoire.")

    article = Article(
        id=str(uuid.uuid4()),
        project_id=project_id,
        category_id=category_id,
        slug=_unique_slug(db, project_id, clean_title),
        search_intent=search_intent,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    set_article_status(article, ArticleStatus.IDEA_PROPOSED)
    db.add(article)
    db.flush()

    revision = ArticleRevision(
        article_id=article.id,
        revision_no=1,
        source=RevisionSource.AI,
        title=clean_title,
        word_count=0,
    )
    db.add(revision)
    db.flush()
    article.current_revision_id = revision.id
    set_primary_keyword(db, project_id, article.id, keyword)
    save_artifact(
        db,
        article.id,
        "editorial_request",
        {
            "keyword": keyword,
            "context_hint": context_hint,
            "audience": audience,
            "angle": angle,
            "source": "editorial_workflow",
        },
    )
    _record_workflow_state(db, article, EditorialStatus.IDEA)
    return article


def technical_checks(article: str, fiche: dict | None, fiche_error: str = "") -> list[dict]:
    """Run exactly the three blocking controls defined by the editorial lab."""
    from experiments.editorial_agent_lab.editorial_agent.checks import blocking_checks

    return blocking_checks(article, fiche, fiche_error)


def validation_report(article: str, fiche: dict | None, fiche_error: str = "") -> dict:
    checks = technical_checks(article, fiche, fiche_error)
    return {"passed": all(check["passed"] for check in checks), "checks": checks}


def _record_workflow_state(db: Session, article: Article, status: EditorialStatus, **extra) -> None:
    save_artifact(
        db,
        article.id,
        WORKFLOW_ARTIFACT_KEY,
        {"managed_by": "editorial_workflow", "status": status.value, **extra},
    )


def _normalise_topic(value: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9àâäéèêëîïôöùûüçñ]+", " ", (value or "").lower())).strip()


def _has_cannibalization(db: Session, article: Article) -> bool:
    title = _normalise_topic(article.current_revision.title if article.current_revision else "")
    keyword = _normalise_topic(primary_keyword(db, article.id))
    if not title and not keyword:
        return False
    candidates = db.execute(
        select(Article).where(
            Article.project_id == article.project_id,
            Article.category_id == article.category_id,
            Article.id != article.id,
            Article.status_reason_id != ArticleStatus.IDEA_REJECTED,
        )
    ).scalars().all()
    for candidate in candidates:
        other_title = _normalise_topic(candidate.current_revision.title if candidate.current_revision else "")
        other_keyword = _normalise_topic(primary_keyword(db, candidate.id))
        if (keyword and keyword == other_keyword) or (title and title == other_title):
            return True
    return False


def workflow_article_details(db: Session, article: Article) -> dict:
    """Return the compact data displayed by the Production screen."""
    from app.services.editorial_score_service import compute_editorial_score

    fiche = get_latest_artifact(db, article.id, FICHE_ARTIFACT_KEY)
    workflow = get_latest_artifact(db, article.id, WORKFLOW_ARTIFACT_KEY) or {}
    writer_report = get_latest_artifact(db, article.id, "editorial_writer_report") or {}
    score = compute_editorial_score(db, article, fiche, workflow.get("fiche_error", ""))
    category = db.get(Category, article.category_id) if article.category_id else None
    return {
        "category_id": article.category_id,
        "category_name": category.name if category else None,
        "keyword": primary_keyword(db, article.id),
        "duplicate": _has_cannibalization(db, article),
        "score": score["global_score"],
        "checks": score["blocking_checks"],
        "alerts": (["plagiat"] if score["plagiarism_alert"] else []) + (["doublon"] if _has_cannibalization(db, article) else []),
        "fiche": fiche,
        "planned_write_at": (get_latest_artifact(db, article.id, "planning_schedule") or {}).get("target_write_at"),
        "cost_usd": writer_report.get("cost_usd"),
        "error": writer_report.get("error"),
    }


def request_writing(db: Session, article: Article, *, commit: bool = True, comment: str | None = None) -> Article:
    set_article_status(article, ArticleStatus.WRITING_REQUESTED)
    if comment:
        article.rejection_note = comment
    article.updated_at = datetime.now(timezone.utc)
    _record_workflow_state(db, article, EditorialStatus.WRITING, comment=comment)
    if commit:
        db.commit()
        db.refresh(article)
    return article


def deposit_markdown(
    db: Session,
    article: Article,
    markdown_content: str,
    fiche: dict | None,
    title: str | None = None,
    fiche_error: str = "",
) -> Article:
    """Store a local writer's Markdown as a new current revision."""
    if not markdown_content.strip():
        raise ValueError("Le contenu Markdown est vide.")

    previous = _latest_revision(db, article.id)
    extracted_title = re.search(r"^#\s+(.+?)\s*$", markdown_content, flags=re.MULTILINE)
    revision = ArticleRevision(
        article_id=article.id,
        revision_no=_next_revision_no(db, article.id),
        source=RevisionSource.AI,
        title=(title or (extracted_title.group(1) if extracted_title else None) or (previous.title if previous else "Article")),
        body=_markdown_to_html(markdown_content),
        faq=(fiche or {}).get("faq", []) if isinstance((fiche or {}).get("faq", []), list) else [],
        word_count=len(markdown_content.split()),
        blocks={"source_format": "markdown"},
    )
    db.add(revision)
    db.flush()
    article.current_revision_id = revision.id
    set_article_status(article, ArticleStatus.REVIEW_NEEDED)
    article.updated_at = datetime.now(timezone.utc)

    if fiche is not None:
        save_artifact(db, article.id, FICHE_ARTIFACT_KEY, fiche)
    score = compute_editorial_score(db, article, fiche, fiche_error)
    store_editorial_score(db, article, score)
    _record_workflow_state(
        db,
        article,
        EditorialStatus.REVIEW,
        fiche_error=fiche_error,
        score=score,
        deposited_at=datetime.now(timezone.utc).isoformat(),
    )

    seo = db.get(ArticleSeo, article.id)
    if seo is None:
        seo = ArticleSeo(article_id=article.id)
        db.add(seo)
    if isinstance(fiche, dict):
        seo.meta_title = fiche.get("meta_title") or seo.meta_title
        seo.meta_description = fiche.get("meta_description") or seo.meta_description

    db.commit()
    db.refresh(article)
    return article


def validate_for_publication(db: Session, article: Article) -> dict:
    revision = _latest_revision(db, article.id)
    fiche = get_latest_artifact(db, article.id, FICHE_ARTIFACT_KEY)
    workflow = get_latest_artifact(db, article.id, WORKFLOW_ARTIFACT_KEY) or {}
    technical = validation_report(revision.body if revision else "", fiche, workflow.get("fiche_error", ""))
    score = compute_editorial_score(db, article, fiche, workflow.get("fiche_error", ""))
    store_editorial_score(db, article, score)
    report = {
        **technical,
        "score": score,
        "global_score": score["global_score"],
        "min_publish_score": resolve_min_publish_score(db.get(Pipeline, article.project_id)),
    }
    report["passed"] = technical["passed"] and score["global_score"] >= report["min_publish_score"]
    if report["passed"]:
        set_article_status(article, ArticleStatus.READY_TO_PUBLISH)
        article.updated_at = datetime.now(timezone.utc)
        _record_workflow_state(db, article, EditorialStatus.VALIDATED, checks=report["checks"], score=score)
        db.commit()
        db.refresh(article)
    return report


def schedule_for_publication(db: Session, article: Article, scheduled_at: datetime) -> dict:
    report = validate_for_publication(db, article)
    if not report["passed"]:
        return report
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
    set_article_status(article, ArticleStatus.SCHEDULED)
    article.scheduled_for = scheduled_at.astimezone(timezone.utc)
    article.updated_at = datetime.now(timezone.utc)
    _record_workflow_state(
        db,
        article,
        EditorialStatus.SCHEDULED,
        scheduled_for=article.scheduled_for.isoformat(),
        checks=report["checks"],
    )
    db.commit()
    db.refresh(article)
    return {**report, "scheduled_for": article.scheduled_for}


def publish_due_article(db: Session, article: Article) -> Article:
    """Publish a scheduled lab article without invoking scoring_service."""
    revision = _latest_revision(db, article.id)
    fiche = get_latest_artifact(db, article.id, FICHE_ARTIFACT_KEY)
    report = validation_report(revision.body if revision else "", fiche)
    if not report["passed"]:
        raise ValueError("Les contrôles techniques ne permettent plus la publication.")
    if revision is None:
        raise ValueError("Aucune révision courante à publier.")

    article.published_revision_id = revision.id
    set_article_status(article, ArticleStatus.PUBLISHED)
    article.published_at = article.published_at or datetime.now(timezone.utc)
    article.scheduled_for = None
    article.updated_at = datetime.now(timezone.utc)
    _record_workflow_state(db, article, EditorialStatus.PUBLISHED, checks=report["checks"])
    db.commit()
    db.refresh(article)
    return article


def is_workflow_managed(db: Session, article_id: str) -> bool:
    artifact = get_latest_artifact(db, article_id, WORKFLOW_ARTIFACT_KEY)
    return bool(artifact and artifact.get("managed_by") == "editorial_workflow")
