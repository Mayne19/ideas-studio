from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.content import Article, Category
from app.models.reference import ArticleStatus
from app.schemas.seo_workflow import CategoryStrategy, asdict
from app.services.seo.artifacts import get_latest_artifacts_bulk

_PENDING_STATUSES = (ArticleStatus.DRAFT, ArticleStatus.DRAFT_READY, ArticleStatus.WRITING_IN_PROGRESS)


def _compute_category_performance(db: Session, project_id: str, category_id: str) -> tuple[float | None, float | None]:
    """Moyenne du CTR et du trafic organique (clics Search Console) des
    articles PUBLIÉS de cette catégorie, à partir de l'artifact
    search_console_metrics (même source que monitoring_agent._compute_
    volatility — aucune table analytics.search_metrics_daily peuplée dans
    ce projet, l'artifact est la seule source réelle disponible).

    Retourne (None, None) si aucun article de la catégorie n'a de données
    de trafic : le scoring appelant doit alors laisser le score inchangé,
    pas supposer une performance nulle."""
    published_ids = db.execute(
        select(Article.id).where(
            Article.project_id == project_id,
            Article.category_id == category_id,
            Article.status_reason_id == ArticleStatus.PUBLISHED,
        )
    ).scalars().all()
    if not published_ids:
        return None, None

    artifacts = get_latest_artifacts_bulk(db, list(published_ids), ["search_console_metrics"])

    ctrs: list[float] = []
    clicks_list: list[float] = []
    for article_id in published_ids:
        metrics = artifacts.get(article_id, {}).get("search_console_metrics")
        if not isinstance(metrics, dict):
            continue
        clicks = metrics.get("clicks")
        impressions = metrics.get("impressions")
        if clicks is None:
            continue
        clicks_list.append(float(clicks))
        if impressions:
            ctrs.append(float(clicks) / float(impressions) * 100.0)

    if not clicks_list:
        return None, None

    avg_ctr = sum(ctrs) / len(ctrs) if ctrs else None
    avg_traffic = sum(clicks_list) / len(clicks_list)
    return avg_ctr, avg_traffic


def _performance_score_adjustment(avg_ctr: float | None, avg_traffic: float | None) -> float:
    """+15 si CTR > 5%, -10 si CTR < 1% ; +10 si trafic > 1000, -5 si < 100.
    0 si la métrique concernée est indisponible (pas de régression du
    scoring existant sans données réelles)."""
    adjustment = 0.0
    if avg_ctr is not None:
        if avg_ctr > 5.0:
            adjustment += 15.0
        elif avg_ctr < 1.0:
            adjustment -= 10.0
    if avg_traffic is not None:
        if avg_traffic > 1000.0:
            adjustment += 10.0
        elif avg_traffic < 100.0:
            adjustment -= 5.0
    return adjustment


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

        avg_ctr, avg_traffic = _compute_category_performance(db, project_id, cat.id)
        performance_adjustment = _performance_score_adjustment(avg_ctr, avg_traffic)
        score += performance_adjustment

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
                "avg_ctr": avg_ctr,
                "avg_traffic": avg_traffic,
                "performance_adjustment": performance_adjustment,
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
        avg_ctr=best_cat["avg_ctr"],
        avg_organic_traffic=best_cat["avg_traffic"],
        performance_score_adjustment=best_cat["performance_adjustment"],
    )
    return result


def compute_category_strategy_dict(db: Session, project_id: str) -> dict:
    return asdict(compute_category_strategy(db, project_id))
