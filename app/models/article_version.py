import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

VERSION_TYPES = ("manual", "autosave", "restore")


class ArticleVersion(Base):
    __tablename__ = "article_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False, index=True)
    article_id: Mapped[str] = mapped_column(String, ForeignKey("articles.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    faq_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    callouts_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_links_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_links_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_blocks_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    version_type: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    created_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
