import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProjectCalloutTemplate(Base):
    __tablename__ = "project_callout_templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    color_background: Mapped[str | None] = mapped_column(String(20), nullable=True)
    color_border: Mapped[str | None] = mapped_column(String(20), nullable=True)
    color_text: Mapped[str | None] = mapped_column(String(20), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
