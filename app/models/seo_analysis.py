import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SeoAnalysis(Base):
    __tablename__ = "seo_analyses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False, index=True)
    article_id: Mapped[str] = mapped_column(String, ForeignKey("articles.id"), nullable=False, index=True)
    seo_score: Mapped[float] = mapped_column(Float, nullable=False)
    readability_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    eeat_score: Mapped[float] = mapped_column(Float, nullable=False)
    readiness_status: Mapped[str] = mapped_column(String(50), nullable=False)  # ready | needs_improvement | blocked
    issues_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    suggestions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
