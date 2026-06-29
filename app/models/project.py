import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    vertical: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    country_target: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reader_level: Mapped[str | None] = mapped_column(String(120), nullable=True)
    writing_style: Mapped[str | None] = mapped_column(String(255), nullable=True)
    editorial_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_proposition: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    forbidden_topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    words_to_avoid: Mapped[str | None] = mapped_column(Text, nullable=True)
    average_target_length: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_formats: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_level: Mapped[str | None] = mapped_column(String(120), nullable=True)
    seo_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    geo_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_guidelines: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_linking_guidelines: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_linking_guidelines: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_examples: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="not_connected", nullable=False)
    public_tracking_key: Mapped[str] = mapped_column(String(86), unique=True, nullable=False)
    secret_api_key: Mapped[str] = mapped_column(String(86), unique=True, nullable=False)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    public_site_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    revalidate_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    revalidate_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_revalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_revalidate_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_revalidate_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def revalidate_secret_configured(self) -> bool:
        return bool(self.revalidate_secret_encrypted)
