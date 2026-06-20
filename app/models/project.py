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
    country_target: Mapped[str | None] = mapped_column(String(10), nullable=True)
    audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
