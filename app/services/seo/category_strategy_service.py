from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.content import Article, Category
from app.models.reference import ArticleStatus
from app.schemas.seo_workflow import CategoryStrategy, asdict

_PENDING_STATUSES = (ArticleStatus.DRAFT, ArticleStatus.DRAFT_READY, ArticleStatus.WRITING_IN_PROGRESS)


def compute_category_strategy(db: Session, project_id: str) -> CategoryStrategy:
    categories = db.execute(select(Category).where(Category.project_id == project_id)).scalars().all()
    if not categories:
        return CategoryStrategy(limitations=["No categories found"])

    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    best_cat = None
    best_score = -1

    for cat in categories:
        priority = float(cat.priority_score) if cat.priority_score is not None else 0
        freq = cat.monthly_target or 0
        pipeline_enabled = cat.is_pipeline_enabled

        if not pipeline_enabled:
            continue

        published_this_month = db.execute(
            select(func.count()).select_from(Article).where(
                Article.project_id == project_id,
                Article.category_id == cat.id,
                Article.status_reason_id == ArticleStatus.PUBLISHED,
                Article.published_at >= first_of_month,
            )
        ).scalar_one()

        pending_drafts = db.execute(
            select(func.count()).select_from(Article).where(
                Article.project_id == project_id,
                Article.category_id == cat.id,
                Article.status_reason_id.in_(_PENDING_STATUSES),
            )
        ).scalar_one()

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
            priority=float(cat.priority_score) if cat.priority_score is not None else 0,
            expected_frequency=cat.monthly_target or 0,
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
