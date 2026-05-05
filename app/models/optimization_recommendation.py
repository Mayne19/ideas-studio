import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

RECOMMENDATION_TYPES = frozenset({
    "improve_title",
    "improve_meta_description",
    "add_faq",
    "add_internal_links",
    "refresh_content",
    "improve_intro",
    "improve_eeat",
    "expand_section",
    "fix_low_traffic",
    "update_keywords",
})

RECOMMENDATION_STATUSES = frozenset({"pending", "accepted", "rejected", "applied"})


class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False, index=True)
    article_id: Mapped[str | None] = mapped_column(String, ForeignKey("articles.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
