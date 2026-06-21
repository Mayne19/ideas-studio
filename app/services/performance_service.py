from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.project import Project
from app.models.traffic_event import TrafficEvent


def _period_window(period: str) -> tuple[datetime, datetime, str]:
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today" or period == "1d":
        return today, now, "hour"
    if period == "yesterday":
        start = today - timedelta(days=1)
        return start, today, "hour"
    days = 30
    if period.endswith("d"):
        try:
            days = int(period[:-1])
        except ValueError:
            pass
    start = today - timedelta(days=max(days - 1, 0))
    if days <= 30:
        return start, now, "day"
    if days <= 180:
        return start, now, "week"
    return start, now, "month"


def _explicit_period_window(
    period: str,
    period_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[datetime, datetime, str]:
    if not start_date or not end_date:
        return _period_window(period)
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    granularity = "day"
    if period_type == "day":
        granularity = "hour"
    elif period_type == "week":
        granularity = "day"
    elif period_type == "month":
        granularity = "day"
    elif period_type in {"quarter", "semester"}:
        granularity = "week"
    elif period_type == "year":
        granularity = "month"
    elif period_type == "custom":
        days = max(1, (end.date() - start.date()).days)
        if days <= 1:
            granularity = "hour"
        elif days <= 93:
            granularity = "day"
        elif days <= 366:
            granularity = "week"
        else:
            granularity = "month"
    return start, end, granularity


def _bucket_key(value: datetime, granularity: str) -> str:
    if granularity == "hour":
        return value.strftime("%H:00")
    if granularity == "week":
        year, week, _ = value.isocalendar()
        return f"{year}-S{week:02d}"
    if granularity == "month":
        return value.strftime("%Y-%m")
    return value.strftime("%Y-%m-%d")


def _empty_buckets(start: datetime, end: datetime, granularity: str) -> list[str]:
    keys: list[str] = []
    cursor = start
    if granularity == "hour":
        while cursor < end:
            keys.append(cursor.strftime("%H:00"))
            cursor += timedelta(hours=1)
        return keys or [start.strftime("%H:00")]
    if granularity == "week":
        cursor = cursor - timedelta(days=cursor.weekday())
        while cursor <= end:
            year, week, _ = cursor.isocalendar()
            keys.append(f"{year}-S{week:02d}")
            cursor += timedelta(days=7)
        return keys
    if granularity == "month":
        cursor = cursor.replace(day=1)
        while cursor <= end:
            keys.append(cursor.strftime("%Y-%m"))
            next_month = 1 if cursor.month == 12 else cursor.month + 1
            next_year = cursor.year + 1 if cursor.month == 12 else cursor.year
            cursor = cursor.replace(year=next_year, month=next_month)
        return keys
    while cursor.date() <= end.date():
        keys.append(cursor.strftime("%Y-%m-%d"))
        cursor += timedelta(days=1)
    return keys


def _source_channel(referrer: str | None) -> str:
    value = (referrer or "").lower()
    if not value:
        return "direct"
    if "google." in value:
        return "organic"
    if any(source in value for source in ("linkedin.", "twitter.", "x.com", "facebook.", "fb.", "reddit.")):
        return "social"
    return "referral"


def get_project_traffic_summary(
    db: Session,
    project_id: str,
    period: str = "30d",
    period_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    since, until, granularity = _explicit_period_window(period, period_type, start_date, end_date)
    project = db.query(Project).filter(Project.id == project_id).first()

    events = (
        db.query(TrafficEvent)
        .filter(
            TrafficEvent.project_id == project_id,
            TrafficEvent.created_at >= since,
            TrafficEvent.created_at < until,
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

    bucket_keys = _empty_buckets(since, until, granularity) if events else []
    trend: dict[str, int] = {key: 0 for key in bucket_keys}
    channel_trend: dict[str, dict[str, int]] = defaultdict(lambda: {
        "direct": 0,
        "organic": 0,
        "social": 0,
        "referral": 0,
    })
    for key in bucket_keys:
        channel_trend[key]
    for e in events:
        bucket = _bucket_key(e.created_at, granularity)
        trend[bucket] = trend.get(bucket, 0) + 1
        channel_trend[bucket][_source_channel(e.referrer)] += 1
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

    since, until, granularity = _period_window(period)

    events = (
        db.query(TrafficEvent)
        .filter(
            TrafficEvent.project_id == article.project_id,
            TrafficEvent.created_at >= since,
            TrafficEvent.created_at < until,
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

    daily: dict[str, int] = {key: 0 for key in _empty_buckets(since, until, granularity)} if matching else {}
    for e in matching:
        day = _bucket_key(e.created_at, granularity)
        daily[day] = daily.get(day, 0) + 1
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


def get_all_articles_performance(
    db: Session,
    project_id: str,
    period: str = "30d",
    period_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    since, until, _granularity = _explicit_period_window(period, period_type, start_date, end_date)
    # Previous period for variation calculation
    if start_date and end_date:
        period_days = max(1, (until.date() - since.date()).days)
    elif period in {"today", "yesterday", "1d"}:
        period_days = 1
    else:
        period_days = int(period.replace("d", "")) if period.endswith("d") else 30
    prev_since = since - timedelta(days=period_days)

    articles = (
        db.query(Article)
        .filter(Article.project_id == project_id, Article.status == "published")
        .all()
    )

    all_events = (
        db.query(TrafficEvent)
        .filter(
            TrafficEvent.project_id == project_id,
            TrafficEvent.created_at >= prev_since,
            TrafficEvent.created_at < until,
        )
        .all()
    )

    results = []
    for article in articles:
        slug = article.slug or ""
        current_matching = [e for e in all_events if slug and (slug in (e.path or e.url)) and since <= e.created_at < until]
        prev_matching = [e for e in all_events if slug and (slug in (e.path or e.url)) and e.created_at < since]
        current_views = len(current_matching)
        prev_views = len(prev_matching)
        variation = None
        if prev_views > 0:
            variation = round((current_views - prev_views) / prev_views * 100, 1)
        elif current_views > 0:
            variation = 100.0
        results.append({
            "article_id": article.id,
            "title": article.title,
            "slug": article.slug,
            "views": current_views,
            "variation": variation,
            "seo_score": article.seo_score,
            "published_at": article.published_at.isoformat() if article.published_at else None,
        })

    results.sort(key=lambda x: x["views"], reverse=True)
    return results
