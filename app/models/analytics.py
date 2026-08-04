"""Schéma analytics — trafic public et recommandations d'optimisation."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import CHAR, ForeignKey, ForeignKeyConstraint, Index, Numeric, SmallInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TrafficEvent(Base):
    """Table partitionnée par mois (analytics.traffic_events_2026_08, ...)."""

    __tablename__ = "traffic_events"
    __table_args__ = (
        Index("traffic_project_time_idx", "project_id", text("occurred_at DESC")),
        {"schema": "analytics"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    occurred_at: Mapped[datetime] = mapped_column(primary_key=True, default=_now)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    article_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    referrer_host: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(CHAR(2), nullable=True)
    device: Mapped[str | None] = mapped_column(Text, nullable=True)
    browser: Mapped[str | None] = mapped_column(Text, nullable=True)
    visitor_hash: Mapped[str | None] = mapped_column(Text, nullable=True)


class SearchMetricsDaily(Base):
    __tablename__ = "search_metrics_daily"
    __table_args__ = {"schema": "analytics"}

    article_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), primary_key=True
    )
    metric_date: Mapped[date] = mapped_column(primary_key=True)
    impressions: Mapped[int] = mapped_column(nullable=False, default=0)
    clicks: Mapped[int] = mapped_column(nullable=False, default=0)
    ctr: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    avg_position: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)


class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["status_reason_id", "state_id"],
            ["ref.run_status_reasons.id", "ref.run_status_reasons.state_id"],
        ),
        {"schema": "analytics"},
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("content.articles.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    state_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status_reason_id: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=10)
    created_at: Mapped[datetime] = mapped_column(default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
