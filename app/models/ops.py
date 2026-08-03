"""Schéma ops — journal d'activité, notifications, webhooks."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import ARRAY, Boolean, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EventLog(Base):
    """Table partitionnée par mois (ops.event_logs_2026_08, ...). Fusionne
    les anciens ArticleLog + ActivityLog (REPRENDRE-LA-MAIN.md §5)."""

    __tablename__ = "event_logs"
    __table_args__ = {"schema": "ops"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    occurred_at: Mapped[datetime] = mapped_column(primary_key=True, default=_now)
    project_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    article_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    level_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.log_levels.id"), nullable=False, default=20)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "ops"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.users.id", ondelete="CASCADE"), nullable=True
    )
    type: Mapped[str] = mapped_column(Text, nullable=False, default="system")
    level_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("ref.log_levels.id"), nullable=False, default=20)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class Webhook(Base):
    __tablename__ = "webhooks"
    __table_args__ = {"schema": "ops"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    events: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    secret_ref: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(default=_now)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = {"schema": "ops"}

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ops.webhooks.id", ondelete="CASCADE"), nullable=False
    )
    event: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    delivered_at: Mapped[datetime] = mapped_column(default=_now)
