from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.project import Project
from app.models.traffic_event import TrafficEvent


def _parse_period(period: str) -> datetime:
    days = 30
    if period.endswith("d"):
        try:
            days = int(period[:-1])
        except ValueError:
            pass
    return datetime.now(timezone.utc) - timedelta(days=days)


def _source_channel(referrer: str | None) -> str:
    value = (referrer or "").lower()
    if not value:
        return "direct"
    if "google." in value:
        return "organic"
    if any(source in value for source in ("linkedin.", "twitter.", "x.com", "facebook.", "fb.", "reddit.")):
        return "social"
    return "referral"


def get_project_traffic_summary(db: Session, project_id: str, period: str = "30d") -> dict:
    since = _parse_period(period)
    project = db.query(Project).filter(Project.id == project_id).first()

    events = (
        db.query(TrafficEvent)
        .filter(
            TrafficEvent.project_id == project_id,
            TrafficEvent.created_at >= since,
        )
        .all()
    )

    _LOCALHOST_PATTERNS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")
    events = [e for e in events if not any(p in (e.url or "").lower() for p in _LOCALHOST_PATTERNS)]

    total_views = len(events)
    if not project or not project.domain:
        tracking_status = "not_configured"
    elif total_views > 0:
        tracking_status = "connected_with_data"
    else:
        tracking_status = "configured_no_data"

    unique_pages = len({e.path or e.url for e in events})

    path_counts = Counter(e.path or e.url for e in events)
    top_pages = [{"path": p, "views": c} for p, c in path_counts.most_common(10)]

    referrer_counts = Counter(e.referrer or "" for e in events)
    referrers = [{"referrer": r, "views": c} for r, c in referrer_counts.most_common(10)]

    country_counts = Counter(e.country for e in events if e.country)
    countries = [{"country": c, "views": v} for c, v in country_counts.most_common(10)]

    device_counts = Counter(e.device for e in events if e.device)
    devices = [{"device": d, "views": c} for d, c in device_counts.most_common(5)]

    trend: dict[str, int] = defaultdict(int)
    channel_trend: dict[str, dict[str, int]] = defaultdict(lambda: {
        "direct": 0,
        "organic": 0,
        "social": 0,
        "referral": 0,
    })
    for e in events:
        day = e.created_at.strftime("%Y-%m-%d")
        trend[day] += 1
        channel_trend[day][_source_channel(e.referrer)] += 1
    trend_by_day = [{"date": d, "views": v} for d, v in sorted(trend.items())]
    channel_trend_by_day = [
        {
            "date": day,
            "direct": values["direct"],
            "organic": values["organic"],
            "social": values["social"],
            "referral": values["referral"],
        }
        for day, values in sorted(channel_trend.items())
    ]

    return {
        "tracking_status": tracking_status,
        "total_views": total_views,
        "unique_pages": unique_pages,
        "top_pages": top_pages,
        "referrers": referrers,
        "countries": countries,
        "devices": devices,
        "trend_by_day": trend_by_day,
        "channel_trend_by_day": channel_trend_by_day,
        "period": period,
    }


def get_article_performance(db: Session, article_id: str, period: str = "30d") -> dict:
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        return {"views": 0, "referrers": [], "countries": [], "daily_views": [], "last_seen_at": None}

    since = _parse_period(period)

    events = (
        db.query(TrafficEvent)
        .filter(
            TrafficEvent.project_id == article.project_id,
            TrafficEvent.created_at >= since,
        )
        .all()
    )

    article_slug = article.slug or ""
    matching = [e for e in events if article_slug and (article_slug in (e.path or e.url))]

    views = len(matching)

    referrer_counts = Counter(e.referrer or "" for e in matching)
    referrers = [{"referrer": r, "views": c} for r, c in referrer_counts.most_common(10)]

    country_counts = Counter(e.country for e in matching if e.country)
    countries = [{"country": c, "views": v} for c, v in country_counts.most_common(10)]

    daily: dict[str, int] = defaultdict(int)
    for e in matching:
        day = e.created_at.strftime("%Y-%m-%d")
        daily[day] += 1
    daily_views = [{"date": d, "views": v} for d, v in sorted(daily.items())]

    last_event = max((e.created_at for e in matching), default=None)

    return {
        "article_id": article_id,
        "views": views,
        "referrers": referrers,
        "countries": countries,
        "daily_views": daily_views,
        "last_seen_at": last_event.isoformat() if last_event else None,
        "period": period,
    }


def get_all_articles_performance(db: Session, project_id: str, period: str = "30d") -> list[dict]:
    since = _parse_period(period)

    articles = (
        db.query(Article)
        .filter(Article.project_id == project_id, Article.status == "published")
        .all()
    )

    events = (
        db.query(TrafficEvent)
        .filter(
            TrafficEvent.project_id == project_id,
            TrafficEvent.created_at >= since,
        )
        .all()
    )

    results = []
    for article in articles:
        slug = article.slug or ""
        matching = [e for e in events if slug and (slug in (e.path or e.url))]
        results.append({
            "article_id": article.id,
            "title": article.title,
            "slug": article.slug,
            "views": len(matching),
            "seo_score": article.seo_score,
            "published_at": article.published_at.isoformat() if article.published_at else None,
        })

    results.sort(key=lambda x: x["views"], reverse=True)
    return results
