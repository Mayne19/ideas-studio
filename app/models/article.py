import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

ARTICLE_STATUSES = frozenset({
    "draft",
    "idea_proposed",
    "idea_priority",
    "idea_rejected",
    "outline_ready",
    "writing_requested",
    "writing_in_progress",
    "draft_ready",
    "review_needed",
    "correction_needed",
    "scheduled",
    "published",
    "failed",
    "update_recommended",
    "ready_to_publish",
    "unpublished",
    "archived",
})

# Statuses a writer role is allowed to edit
WRITER_EDITABLE_STATUSES = frozenset({
    "draft", "draft_ready", "review_needed", "correction_needed", "ready_to_publish"
})


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False, index=True)
    category_id: Mapped[str | None] = mapped_column(String, ForeignKey("categories.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False, index=True)
    keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secondary_keywords_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str | None] = mapped_column(String(500), nullable=True)
    angle: Mapped[str | None] = mapped_column(String(500), nullable=True)
    search_intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    outline_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    serp_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    opportunity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seo_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    eeat_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    readiness_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    seo_review_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    project_context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    category_strategy_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    idea_discovery_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    intent_analysis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    research_brief_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    keyword_brief_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cannibalization_check_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    editorial_angle_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    image_sources_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    callout_plan_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    language_quality_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    originality_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    humanization_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    eeat_checklist_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    editorial_quality_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seo_final_checklist_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generation_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sources_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    faq_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    callouts_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    internal_links_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_links_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_console_metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_blocks_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejection_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_update_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reading_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    published_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_meta_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_cover_image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    published_faq_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_callouts_json: Mapped[str | None] = mapped_column(Text, nullable=True)
