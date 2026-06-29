import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from calendar import monthrange
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.article import Article
from app.models.category import Category
from app.services.idea_engine import generate_idea
from app.services.log_service import log_step

logger = logging.getLogger(__name__)

DEFAULT_GENERATION_DAY = 27


def _get_next_month_range() -> tuple[datetime, datetime, int]:
    """Get the start, end, and number of days for the next month."""
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month + 1
    if month > 12:
        month = 1
        year += 1
    days_in_month = monthrange(year, month)[1]
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year, month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)
    return start, end, days_in_month


def _distribute_dates(
    total_ideas: int,
    month_start: datetime,
    days_in_month: int,
    category_frequencies: dict[str, int],
    category_niches: dict[str, str | None] | None = None,
) -> dict[str, list[datetime]]:
    """Distribute ideas across the month avoiding same-category and same-niche on the same day."""
    import random
    rng = random.Random(42)  # deterministic for reproducibility

    available_dates = [
        month_start + timedelta(days=d)
        for d in range(2, days_in_month - 1)
    ]
    rng.shuffle(available_dates)

    niches = category_niches or {}
    # day_key -> set of categories assigned that day
    day_categories: dict[str, set[str]] = {}
    # day_key -> set of niches assigned that day
    day_niches: dict[str, set[str]] = {}

    result: dict[str, list[datetime]] = {}

    for category_id, freq in sorted(category_frequencies.items(), key=lambda x: -x[1]):
        niche = niches.get(category_id)
        dates: list[datetime] = []
        remaining_pool = list(available_dates)

        for _ in range(freq):
            assigned = False
            # Try to find a date with no niche conflict (ideal: 0 per niche per day)
            for date in remaining_pool:
                day_key = date.strftime("%Y-%m-%d")
                used_cats = day_categories.get(day_key, set())
                used_niches = day_niches.get(day_key, set())
                if category_id in used_cats:
                    continue
                if niche and niche in used_niches:
                    continue
                # Accept this date
                dates.append(date)
                day_categories.setdefault(day_key, set()).add(category_id)
                if niche:
                    day_niches.setdefault(day_key, set()).add(niche)
                remaining_pool.remove(date)
                assigned = True
                break

            if not assigned:
                # All dates have a niche conflict; accept the first available without category conflict
                for date in remaining_pool:
                    day_key = date.strftime("%Y-%m-%d")
                    if category_id not in day_categories.get(day_key, set()):
                        dates.append(date)
                        day_categories.setdefault(day_key, set()).add(category_id)
                        if niche:
                            day_niches.setdefault(day_key, set()).add(niche)
                        remaining_pool.remove(date)
                        assigned = True
                        logger.warning(
                            "Niche conflict unavoidable for category %s (niche=%s) — assigning anyway",
                            category_id, niche,
                        )
                        break

            if not assigned:
                logger.warning(
                    "No available dates left for category %s — skipping assignment", category_id
                )

        result[category_id] = dates

    return result


def generate_monthly_plan(
    db: Session,
    project_id: str,
    llm,
    search,
    agent_router=None,
    generation_day: int = DEFAULT_GENERATION_DAY,
    force: bool = False,
) -> dict:
    """Generate ideas for the next month based on category frequencies."""
    from app.models.project import Project
    project = db.get(Project, project_id)
    if not project:
        return {"error": "Project not found"}

    # Get categories with their target frequencies
    categories = db.execute(
        select(Category).where(
            Category.project_id == project_id,
        )
    ).scalars().all()

    today = datetime.now(timezone.utc).day

    # Only auto-generate on or after generation_day, unless forced
    if today < generation_day and not force:
        return {
            "status": "skipped",
            "message": f"Auto-génération prévue le {generation_day} du mois (aujourd'hui : {today})",
        }

    month_start, month_end, days_in_month = _get_next_month_range()

    # Calculate total ideas needed
    category_frequencies: dict[str, int] = {}
    total_ideas = 0
    for cat in categories:
        freq = cat.target_frequency or 1
        category_frequencies[cat.id] = freq
        total_ideas += freq

    if total_ideas == 0:
        total_ideas = max(1, len(categories))
        for cat in categories:
            category_frequencies[cat.id] = 1

    # Build niche map for anti-collision
    category_niches: dict[str, str | None] = {
        cat.id: getattr(cat, "niche", None) for cat in categories
    }

    # Distribute dates
    date_distribution = _distribute_dates(
        total_ideas, month_start, days_in_month, category_frequencies, category_niches
    )

    # Generate ideas
    ideas_generated = 0
    errors = []
    write_dates: list[datetime] = []
    review_dates: list[datetime] = []

    # Generate write/review dates (write = 1 week before publish, review = 3 days before publish)
    for cat_dates in date_distribution.values():
        for pub_date in cat_dates:
            write_date = pub_date - timedelta(days=7)
            review_date = pub_date - timedelta(days=3)
            write_dates.append(write_date)
            review_dates.append(review_date)

    date_index = 0

    for category_id, freq in sorted(category_frequencies.items(), key=lambda x: -x[1]):
        cat = next((c for c in categories if c.id == category_id), None)
        for i in range(freq):
            try:
                article = generate_idea(
                    db=db,
                    project_id=project_id,
                    project_audience=project.audience,
                    project_language=project.language or "fr",
                    llm=llm,
                    search=search,
                    category_id=category_id,
                    agent_router=agent_router,
                )
                if article:
                    # Set target dates
                    if date_index < len(write_dates):
                        article.target_write_at = write_dates[date_index]
                    if date_index < len(review_dates):
                        article.target_review_at = review_dates[date_index]
                    if date_index < len(cat_dates := date_distribution.get(category_id, [])):
                        article.scheduled_at = cat_dates[i] if i < len(cat_dates) else None

                    ideas_generated += 1
                    date_index += 1

                    log_step(
                        db, project_id,
                        f"Idée planifiée générée : {article.title} (catégorie : {cat.name if cat else 'aucune'})",
                        level="info", step="monthly_planning", article_id=article.id,
                    )
            except Exception as exc:
                logger.exception("Monthly planning idea generation failed")
                errors.append(str(exc))

    if ideas_generated > 0:
        db.commit()

    return {
        "status": "completed",
        "month": month_start.strftime("%Y-%m"),
        "ideas_generated": ideas_generated,
        "categories_used": len(category_frequencies),
        "errors": errors if errors else None,
    }
