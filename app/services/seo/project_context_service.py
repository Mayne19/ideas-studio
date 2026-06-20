from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.project import Project
from app.models.pipeline import ProjectPipeline
from app.models.category import Category
from app.schemas.seo_workflow import ProjectContext, asdict
from app.services.seo.helpers import safe_json_load


def build_project_context(db: Session, project_id: str) -> ProjectContext:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return ProjectContext(limitations=["Project not found"])

    categories = db.query(Category).filter(Category.project_id == project_id).all()
    articles = db.query(Article).filter(Article.project_id == project_id).all()

    published = [a for a in articles if a.status == "published"]
    drafts = [a for a in articles if a.status in ("draft", "draft_ready", "writing_in_progress")]
    ideas = [a for a in articles if a.status in ("idea_proposed", "idea_priority")]

    recent_topics = []
    known_keywords = []
    for a in sorted(published, key=lambda x: x.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:20]:
        if a.title:
            recent_topics.append(a.title)
        if a.keyword:
            known_keywords.append(a.keyword)
    for a in drafts + ideas:
        if a.keyword and a.keyword not in known_keywords:
            known_keywords.append(a.keyword)

    pipeline = db.query(ProjectPipeline).filter(ProjectPipeline.project_id == project_id).first()
    pipeline_settings = None
    if pipeline:
        pipeline_settings = {
            "enabled": pipeline.enabled,
            "active_days": safe_json_load(pipeline.active_days, []),
            "launch_hour": pipeline.launch_hour,
            "articles_per_week": pipeline.articles_per_week,
        }

    strategy_parts = [
        ("description", project.description),
        ("industry", project.industry),
        ("tone", project.tone),
        ("reader_level", project.reader_level),
        ("writing_style", project.writing_style),
        ("editorial_goal", project.editorial_goal),
        ("value_proposition", project.value_proposition),
        ("allowed_topics", project.allowed_topics),
        ("forbidden_topics", project.forbidden_topics),
        ("words_to_avoid", project.words_to_avoid),
        ("average_target_length", project.average_target_length),
        ("preferred_formats", project.preferred_formats),
        ("technical_level", project.technical_level),
        ("seo_rules", project.seo_rules),
        ("geo_rules", project.geo_rules),
        ("source_guidelines", project.source_guidelines),
        ("internal_linking_guidelines", project.internal_linking_guidelines),
        ("external_linking_guidelines", project.external_linking_guidelines),
        ("style_examples", project.style_examples),
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
        categories=[{"id": c.id, "name": c.name, "slug": c.slug, "priority": c.priority} for c in categories],
        active_categories=[{"id": c.id, "name": c.name, "slug": c.slug, "priority": c.priority} for c in categories if getattr(c, "pipeline_enabled", True)],
        published_articles_count=len(published),
        draft_articles_count=len(drafts),
        recent_topics=recent_topics,
        known_keywords=known_keywords,
        editorial_notes=editorial_notes,
        target_audience=project.audience,
        pipeline_settings=pipeline_settings,
        limitations=[],
    )


def build_project_context_dict(db: Session, project_id: str) -> dict:
    return asdict(build_project_context(db, project_id))
