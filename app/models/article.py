import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
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
    "blocked_cost_limit",
    "update_recommended",
    "ready_to_publish",
    "unpublished",
    "archived",
    # Monitoring / improvement statuses
    "improvement_proposed",
    "improvement_in_progress",
    "improvement_ready",
})

# Statuses a designer role is allowed to edit
DESIGNER_EDITABLE_STATUSES = frozenset({
    "draft", "draft_ready", "review_needed", "correction_needed", "ready_to_publish"
})


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), nullable=False, index=True)
    category_id: Mapped[str | None] = mapped_column(String, ForeignKey("categories.id"), nullable=True)
    sub_niche: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
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
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
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
    readability_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    editorial_quality_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seo_final_checklist_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generation_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sources_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    serp_analysis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    extracted_sources_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    content_gap_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_quality_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_pack_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    style_guide_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cannibalization_outline_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    claims_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fact_check_report_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    estimated_cost_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    geo_optimization_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    structured_data_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    human_insights_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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

    # --- Global score ---
    global_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    global_score_valid: Mapped[bool | None] = mapped_column(Integer, nullable=True)

    # --- Editorial dates ---
    idea_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    idea_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    human_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Workflow tracking ---
    workflow_run_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    completed_agent_keys: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_agent_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_outputs_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    planning_brief_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    production_brief_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    workflow_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # --- Target dates ---
    target_write_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Pre-brief fields ---
    main_answer_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    opportunity_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_format: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_format: Mapped[str | None] = mapped_column(String(20), nullable=True)  # short|medium|long|pillar
    needs_faq: Mapped[bool | None] = mapped_column(Integer, nullable=True)
    needs_images: Mapped[bool | None] = mapped_column(Integer, nullable=True)
    suggested_internal_links: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_external_links: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proposal_source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Monitoring / improvement ---
    improvement_proposal_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    performance_diagnosis_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    original_article_id: Mapped[str | None] = mapped_column(String, ForeignKey("articles.id"), nullable=True)
    revision_of_article_id: Mapped[str | None] = mapped_column(String, ForeignKey("articles.id"), nullable=True)
    proposed_changes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    improvement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    monitoring_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
