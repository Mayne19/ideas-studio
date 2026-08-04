from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from functools import lru_cache

logger = logging.getLogger(__name__)


def _get_client(service_account_json: str):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.oauth2 import service_account

    creds_dict = json.loads(service_account_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"],
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def _property(property_id: str) -> str:
    return f"properties/{property_id}"


def resolve_ga4_credentials(db, project_id: str | None) -> tuple[str | None, str | None]:
    """Renvoie (property_id, service_account_json) — le projet a priorité,
    repli sur settings.GA4_PROPERTY_ID/GOOGLE_SERVICE_ACCOUNT_JSON si absent."""
    from app.core.config import settings
    from app.core.security import decrypt_secret
    from app.models.core import PublishingTarget
    from sqlalchemy import select

    property_id = None
    service_account_json = None
    if project_id:
        target = db.execute(
            select(PublishingTarget)
            .where(PublishingTarget.project_id == project_id)
            .order_by(PublishingTarget.is_primary.desc(), PublishingTarget.created_at.asc())
            .limit(1)
        ).scalar_one_or_none()
        if target:
            property_id = target.ga4_property_id
            service_account_json = decrypt_secret(target.ga4_service_account_json)

    return (
        property_id or settings.GA4_PROPERTY_ID or None,
        service_account_json or settings.GOOGLE_SERVICE_ACCOUNT_JSON or None,
    )


def get_overview(
    start_date: str = "30daysAgo",
    end_date: str = "today",
    *,
    property_id: str,
    service_account_json: str,
) -> dict:
    from google.analytics.data_v1beta.types import (
        DateRange, Metric, Dimension, RunReportRequest
    )

    try:
        client = _get_client(service_account_json)

        request = RunReportRequest(
            property=_property(property_id),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
                Metric(name="newUsers"),
            ],
        )
        response = client.run_report(request)

        row = response.rows[0] if response.rows else None
        if not row:
            return _empty_overview()

        values = [v.value for v in row.metric_values]
        return {
            "active_users": int(float(values[0])),
            "sessions": int(float(values[1])),
            "page_views": int(float(values[2])),
            "avg_session_duration": round(float(values[3])),
            "bounce_rate": round(float(values[4]) * 100, 1),
            "new_users": int(float(values[5])),
            "period": {"start": start_date, "end": end_date},
            "source": "google_analytics",
        }

    except Exception as exc:
        logger.warning("GA4 overview failed: %s", exc)
        return _empty_overview()


def get_top_articles(
    start_date: str = "30daysAgo",
    end_date: str = "today",
    *,
    property_id: str,
    service_account_json: str,
) -> list[dict]:
    from google.analytics.data_v1beta.types import (
        DateRange, Metric, Dimension, RunReportRequest, OrderBy
    )

    try:
        client = _get_client(service_account_json)

        request = RunReportRequest(
            property=_property(property_id),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name="pagePath"),
                Dimension(name="pageTitle"),
            ],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
                Metric(name="averageSessionDuration"),
            ],
            order_bys=[
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
                    desc=True,
                )
            ],
        )
        response = client.run_report(request)

        articles = []
        for row in response.rows:
            path = row.dimension_values[0].value
            title = row.dimension_values[1].value
            users = int(float(row.metric_values[0].value))
            views = int(float(row.metric_values[1].value))
            duration = round(float(row.metric_values[2].value))

            if path in ("/", "") or len(path) < 3:
                continue

            articles.append({
                "path": path,
                "title": title,
                "users": users,
                "views": views,
                "avg_duration": duration,
            })

        return articles

    except Exception as exc:
        logger.warning("GA4 top_articles failed: %s", exc)
        return []


def get_traffic_sources(
    start_date: str = "30daysAgo",
    end_date: str = "today",
    *,
    property_id: str,
    service_account_json: str,
) -> list[dict]:
    from google.analytics.data_v1beta.types import (
        DateRange, Metric, Dimension, RunReportRequest, OrderBy
    )

    try:
        client = _get_client(service_account_json)

        request = RunReportRequest(
            property=_property(property_id),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
            ],
            order_bys=[
                OrderBy(
                    metric=OrderBy.MetricOrderBy(metric_name="sessions"),
                    desc=True,
                )
            ],
        )
        response = client.run_report(request)

        sources = []
        for row in response.rows:
            sources.append({
                "channel": row.dimension_values[0].value,
                "sessions": int(float(row.metric_values[0].value)),
                "users": int(float(row.metric_values[1].value)),
            })

        return sources

    except Exception as exc:
        logger.warning("GA4 traffic_sources failed: %s", exc)
        return []


def get_evolution(
    start_date: str = "30daysAgo",
    end_date: str = "today",
    *,
    property_id: str,
    service_account_json: str,
) -> list[dict]:
    from google.analytics.data_v1beta.types import (
        DateRange, Metric, Dimension, RunReportRequest, OrderBy
    )

    try:
        client = _get_client(service_account_json)

        request = RunReportRequest(
            property=_property(property_id),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[Dimension(name="date")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="screenPageViews"),
            ],
            order_bys=[
                OrderBy(
                    dimension=OrderBy.DimensionOrderBy(dimension_name="date"),
                    desc=False,
                )
            ],
        )
        response = client.run_report(request)

        evolution = []
        for row in response.rows:
            raw_date = row.dimension_values[0].value
            evolution.append({
                "date": f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}",
                "users": int(float(row.metric_values[0].value)),
                "views": int(float(row.metric_values[1].value)),
            })

        return evolution

    except Exception as exc:
        logger.warning("GA4 evolution failed: %s", exc)
        return []


def get_full_report(
    start_date: str = "30daysAgo",
    end_date: str = "today",
    *,
    property_id: str | None,
    service_account_json: str | None,
) -> dict:
    if not property_id or not service_account_json:
        return {
            "overview": _empty_overview(),
            "top_articles": [],
            "traffic_sources": [],
            "evolution": [],
            "period": {"start": start_date, "end": end_date},
            "source": "not_configured",
        }
    return {
        "overview": get_overview(start_date, end_date, property_id=property_id, service_account_json=service_account_json),
        "top_articles": get_top_articles(start_date, end_date, property_id=property_id, service_account_json=service_account_json),
        "traffic_sources": get_traffic_sources(start_date, end_date, property_id=property_id, service_account_json=service_account_json),
        "evolution": get_evolution(start_date, end_date, property_id=property_id, service_account_json=service_account_json),
        "period": {"start": start_date, "end": end_date},
        "source": "google_analytics",
    }


def _empty_overview() -> dict:
    return {
        "active_users": 0,
        "sessions": 0,
        "page_views": 0,
        "avg_session_duration": 0,
        "bounce_rate": 0,
        "new_users": 0,
        "source": "google_analytics",
    }
