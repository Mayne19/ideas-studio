import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.sqlite import JSON
from app.core.database import Base


class ProjectPipeline(Base):
    __tablename__ = "project_pipelines"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active_days: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    launch_hour: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    articles_per_week: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    category_priorities: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    ideas_per_week: Mapped[int | None] = mapped_column(Integer, default=5, nullable=True)
    max_pending_drafts: Mapped[int | None] = mapped_column(Integer, default=10, nullable=True)
    paused_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_indefinitely: Mapped[bool | None] = mapped_column(Boolean, default=False, nullable=True)
    default_quality_mode: Mapped[str | None] = mapped_column(String(20), default="quality", nullable=True)
    category_strategy_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    launch_hours: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
