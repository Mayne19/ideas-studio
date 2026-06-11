import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class KanbanColumn(Base):
    __tablename__ = "kanban_columns"
    __table_args__ = (UniqueConstraint("project_id", "label", name="uq_kanban_column_label"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#007aff")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
