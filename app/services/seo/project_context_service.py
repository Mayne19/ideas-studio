from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import Pipeline
from app.models.content import Article, ArticleKeyword, ArticleRevision, Category, Keyword, KeywordRole
from app.models.core import Project
from app.models.reference import ArticleStatus
from app.schemas.seo_workflow import ProjectContext, asdict

_PUBLISHED = (ArticleStatus.PUBLISHED,)
_DRAFTS = (ArticleStatus.DRAFT, ArticleStatus.DRAFT_READY, ArticleStatus.WRITING_IN_PROGRESS)
_IDEAS = (ArticleStatus.IDEA_PROPOSED, ArticleStatus.IDEA_PRIORITY)


def build_project_context(db: Session, project_id: str) -> ProjectContext:
    project = db.get(Project, project_id)
    if not project:
        return ProjectContext(limitations=["Project not found"])

    profile = project.active_editorial_profile
    rules = profile.rules if profile else {}
    constraints = profile.constraints if profile else {}

    categories = db.execute(select(Category).where(Category.project_id == project_id)).scalars().all()

    articles = db.execute(select(Article).where(Article.project_id == project_id)).scalars().all()
    published = [a for a in articles if a.status_reason_id in _PUBLISHED]
    drafts = [a for a in articles if a.status_reason_id in _DRAFTS]
    ideas = [a for a in articles if a.status_reason_id in _IDEAS]

    article_ids = [a.id for a in articles]
    revisions_by_article: dict[str, ArticleRevision] = {}
    if article_ids:
        current_ids = [a.current_revision_id for a in articles if a.current_revision_id]
        if current_ids:
            for rev in db.execute(select(ArticleRevision).where(ArticleRevision.id.in_(current_ids))).scalars().all():
                revisions_by_article[rev.article_id] = rev

    primary_keyword_by_article: dict[str, str] = {}
    if article_ids:
        rows = db.execute(
            select(ArticleKeyword.article_id, Keyword.term)
            .join(Keyword, Keyword.id == ArticleKeyword.keyword_id)
            .where(ArticleKeyword.article_id.in_(article_ids), ArticleKeyword.role == KeywordRole.PRIMARY)
        ).all()
        primary_keyword_by_article = dict(rows)

    recent_topics = []
    known_keywords = []
    used_angles: list[str] = []
    used_examples: list[str] = []
    for a in sorted(published, key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:20]:
        rev = revisions_by_article.get(a.id)
        if rev and rev.title:
            recent_topics.append(rev.title)
        kw = primary_keyword_by_article.get(a.id)
        if kw:
            known_keywords.append(kw)
    for a in drafts + ideas:
        kw = primary_keyword_by_article.get(a.id)
        if kw and kw not in known_keywords:
            known_keywords.append(kw)

    # Angles et exemples déjà utilisés sur le projet (depuis les artifacts) —
    # évite de réutiliser un angle éditorial ou un exemple déjà exploité dans
    # un article publié ou en cours (FIX 24).
    for a in published + drafts:
        from app.services.seo.artifacts import get_latest_artifact
        angle = get_latest_artifact(db, a.id, "editorial_angle")
        if isinstance(angle, dict):
            main_angle = angle.get("main_angle")
            if main_angle and main_angle not in used_angles:
                used_angles.append(str(main_angle))
            differentiation = angle.get("differentiation")
            if differentiation and str(differentiation) not in used_angles:
                used_angles.append(str(differentiation))
        insights = get_latest_artifact(db, a.id, "human_insights")
        if isinstance(insights, dict):
            for ex in (insights.get("real_examples") or [])[:4]:
                if isinstance(ex, str) and ex not in used_examples:
                    used_examples.append(ex)

    pipeline = db.get(Pipeline, project_id)
    pipeline_settings = None
    if pipeline:
        pipeline_settings = {
            "enabled": pipeline.is_enabled,
            "active_days": (pipeline.schedule or {}).get("active_days", []),
            "launch_hour": (pipeline.schedule or {}).get("launch_hour"),
            "articles_per_week": pipeline.articles_per_week,
        }

    strategy_parts = [
        ("audience", profile.audience if profile else None),
        ("tone", profile.tone if profile else None),
        ("reader_level", profile.reader_level if profile else None),
        ("writing_style", profile.writing_style if profile else None),
        ("site_description", rules.get("description")),
        ("positioning", rules.get("positioning")),
        ("priority_keywords", ", ".join(rules.get("main_keywords") or []) or None),
        ("editorial_goal", rules.get("editorial_goal")),
        ("value_proposition", rules.get("value_proposition")),
        ("allowed_topics", rules.get("allowed_topics")),
        ("forbidden_topics", constraints.get("forbidden_topics")),
        ("words_to_avoid", constraints.get("words_to_avoid")),
        ("preferred_formats", rules.get("preferred_formats")),
        ("technical_level", rules.get("technical_level")),
        ("seo_rules", rules.get("seo_rules")),
        ("geo_rules", rules.get("geo_rules")),
        ("source_guidelines", rules.get("source_guidelines")),
        ("internal_linking_guidelines", rules.get("internal_linking_guidelines")),
        ("external_linking_guidelines", rules.get("external_linking_guidelines")),
        ("style_examples", rules.get("style_examples")),
    ]
    editorial_notes = "\n".join(
        f"{key}: {value}"
        for key, value in strategy_parts
        if value
    ) or None

    return ProjectContext(
        project_id=project_id,
        site_url=project.domain or "",
        project_name=project.name or "",
        categories=[{"id": c.id, "name": c.name, "slug": c.slug, "priority": float(c.priority_score) if c.priority_score is not None else None} for c in categories],
        active_categories=[{"id": c.id, "name": c.name, "slug": c.slug, "priority": float(c.priority_score) if c.priority_score is not None else None} for c in categories if c.is_pipeline_enabled],
        published_articles_count=len(published),
        draft_articles_count=len(drafts),
        recent_topics=recent_topics,
        known_keywords=known_keywords,
        used_angles=used_angles[:20],
        used_examples=used_examples[:20],
        editorial_notes=editorial_notes,
        target_audience=profile.audience if profile else None,
        pipeline_settings=pipeline_settings,
        limitations=[],
    )


def build_project_context_dict(db: Session, project_id: str) -> dict:
    return asdict(build_project_context(db, project_id))
