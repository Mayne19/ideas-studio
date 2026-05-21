from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.article import Article
from app.models.category import Category
from app.schemas.seo_workflow import CategoryStrategy, asdict


def compute_category_strategy(db: Session, project_id: str) -> CategoryStrategy:
    categories = db.query(Category).filter(Category.project_id == project_id).all()
    if not categories:
        return CategoryStrategy(limitations=["No categories found"])

    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    best_cat = None
    best_score = -1

    for cat in categories:
        priority = getattr(cat, "priority_score", None) or cat.priority or 0
        freq = getattr(cat, "monthly_frequency", None) or getattr(cat, "target_frequency", None) or 0
        pipeline_enabled = getattr(cat, "pipeline_enabled", True)

        published_this_month = db.query(Article).filter(
            Article.project_id == project_id,
            Article.category_id == cat.id,
            Article.status == "published",
            Article.published_at >= first_of_month,
        ).count()

        pending_drafts = db.query(Article).filter(
            Article.project_id == project_id,
            Article.category_id == cat.id,
            Article.status.in_(["draft", "draft_ready", "writing_in_progress"]),
        ).count()

        if not pipeline_enabled:
            continue

        saturation_ratio = published_this_month / max(freq, 1) if freq > 0 else 0
        underfed = freq > 0 and published_this_month < freq * 0.5
        saturated = saturation_ratio > 1.2

        score = priority * 10 - published_this_month * 2 - pending_drafts * 3
        if underfed:
            score += 20
        if saturated:
            score -= 50

        if score > best_score:
            best_score = score
            best_cat = {
                "cat": cat,
                "priority": priority,
                "freq": freq,
                "published_this_month": published_this_month,
                "pending_drafts": pending_drafts,
                "saturation_ratio": saturation_ratio,
                "underfed": underfed,
                "saturated": saturated,
            }

    if not best_cat:
        cat = categories[0]
        return CategoryStrategy(
            chosen_category_id=cat.id,
            chosen_category_name=cat.name,
            reason="No better option available",
            priority=cat.priority or 0,
            expected_frequency=getattr(cat, "target_frequency", None) or 0,
            limitations=["All categories saturated or disabled"],
        )

    result = CategoryStrategy(
        chosen_category_id=best_cat["cat"].id,
        chosen_category_name=best_cat["cat"].name,
        reason="Selected by priority/frequency heuristic",
        priority=best_cat["priority"],
        expected_frequency=best_cat["freq"],
        articles_published_this_month=best_cat["published_this_month"],
        pending_drafts=best_cat["pending_drafts"],
        saturation_risk="high" if best_cat["saturated"] else ("medium" if best_cat["saturation_ratio"] > 0.8 else "low"),
        underfed=best_cat["underfed"],
        saturated=best_cat["saturated"],
    )
    return result


def compute_category_strategy_dict(db: Session, project_id: str) -> dict:
    return asdict(compute_category_strategy(db, project_id))
