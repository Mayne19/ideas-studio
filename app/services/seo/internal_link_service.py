from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.category import Category
from app.schemas.seo_workflow import InternalLinkPlan, asdict
from app.services.seo.helpers import normalize_text


def build_internal_link_plan(
    db: Session,
    project_id: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
    limit: int = 5,
) -> InternalLinkPlan:
    plan = InternalLinkPlan()

    articles = db.query(Article).filter(
        Article.project_id == project_id,
        Article.status == "published",
    ).all()

    if exclude_article_id:
        articles = [a for a in articles if a.id != exclude_article_id]

    normalized_keyword = normalize_text(keyword)
    scored = []

    for a in articles:
        score = 0
        a_title = normalize_text(a.title or "")
        a_keyword = normalize_text(a.keyword or "")

        if a_keyword and normalized_keyword in a_keyword:
            score += 10
        if a_title and normalized_keyword in a_title:
            score += 5
        if a.category_id and category_id and a.category_id == category_id:
            score += 3

        if score > 0:
            cat_name = None
            if a.category_id:
                cat = db.query(Category).filter(Category.id == a.category_id).first()
                cat_name = cat.name if cat else None

            scored.append({
                "target_article_id": a.id,
                "target_url": f"/articles/{a.slug}",
                "anchor_text": a.title or "Article connexe",
                "placement": "auto",
                "reason": f"Pertinence {score}/10",
                "relevance_score": score,
                "category": cat_name,
            })

    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    plan.links = scored[:limit]

    if not plan.links:
        plan.limitations.append("No relevant internal articles found")

    return plan


def build_internal_link_plan_dict(
    db: Session,
    project_id: str,
    keyword: str,
    category_id: str | None = None,
    exclude_article_id: str | None = None,
    limit: int = 5,
) -> dict:
    return asdict(build_internal_link_plan(db, project_id, keyword, category_id, exclude_article_id, limit))
