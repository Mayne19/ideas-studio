"""add seo workflow fields to article, category, pipeline

Revision ID: 014_seo_workflow_fields
Revises: 013_article_seo_review_json
Create Date: 2026-05-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "014_seo_workflow_fields"
down_revision = "013_article_seo_review_json"
branch_labels = None
depends_on = None


def column_exists(table, column):
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    # Article workflow JSON fields
    for col in (
        "project_context_json", "category_strategy_json", "idea_discovery_json",
        "intent_analysis_json", "research_brief_json", "keyword_brief_json",
        "cannibalization_check_json", "editorial_angle_json", "image_plan_json",
        "image_sources_json", "callout_plan_json", "language_quality_report_json",
        "originality_report_json", "humanization_report_json", "eeat_checklist_json",
        "editorial_quality_report_json", "seo_final_checklist_json",
        "generation_report_json", "sources_json",
    ):
        if not column_exists("articles", col):
            op.add_column("articles", sa.Column(col, sa.JSON(), nullable=True))

    # Category extra fields
    if not column_exists("categories", "priority_score"):
        op.add_column("categories", sa.Column("priority_score", sa.Float(), nullable=True))
    if not column_exists("categories", "monthly_frequency"):
        op.add_column("categories", sa.Column("monthly_frequency", sa.Integer(), nullable=True))
    if not column_exists("categories", "pipeline_enabled"):
        op.add_column("categories", sa.Column("pipeline_enabled", sa.Boolean(), nullable=True, server_default=sa.text("1")))
    if not column_exists("categories", "editorial_goal"):
        op.add_column("categories", sa.Column("editorial_goal", sa.Text(), nullable=True))
    if not column_exists("categories", "target_audience"):
        op.add_column("categories", sa.Column("target_audience", sa.Text(), nullable=True))
    if not column_exists("categories", "internal_notes"):
        op.add_column("categories", sa.Column("internal_notes", sa.Text(), nullable=True))

    # Pipeline extra fields
    if not column_exists("project_pipelines", "ideas_per_week"):
        op.add_column("project_pipelines", sa.Column("ideas_per_week", sa.Integer(), nullable=True, server_default=sa.text("5")))
    if not column_exists("project_pipelines", "max_pending_drafts"):
        op.add_column("project_pipelines", sa.Column("max_pending_drafts", sa.Integer(), nullable=True, server_default=sa.text("10")))
    if not column_exists("project_pipelines", "paused_until"):
        op.add_column("project_pipelines", sa.Column("paused_until", sa.DateTime(timezone=True), nullable=True))
    if not column_exists("project_pipelines", "paused_indefinitely"):
        op.add_column("project_pipelines", sa.Column("paused_indefinitely", sa.Boolean(), nullable=True, server_default=sa.text("0")))
    if not column_exists("project_pipelines", "default_quality_mode"):
        op.add_column("project_pipelines", sa.Column("default_quality_mode", sa.String(20), nullable=True, server_default=sa.text("'quality'")))
    if not column_exists("project_pipelines", "category_strategy_json"):
        op.add_column("project_pipelines", sa.Column("category_strategy_json", sa.JSON(), nullable=True))
    if not column_exists("project_pipelines", "launch_hours"):
        op.add_column("project_pipelines", sa.Column("launch_hours", sa.Text(), nullable=True))


def downgrade() -> None:
    for col in (
        "project_context_json", "category_strategy_json", "idea_discovery_json",
        "intent_analysis_json", "research_brief_json", "keyword_brief_json",
        "cannibalization_check_json", "editorial_angle_json", "image_plan_json",
        "image_sources_json", "callout_plan_json", "language_quality_report_json",
        "originality_report_json", "humanization_report_json", "eeat_checklist_json",
        "editorial_quality_report_json", "seo_final_checklist_json",
        "generation_report_json", "sources_json",
    ):
        if column_exists("articles", col):
            op.drop_column("articles", col)

    for col in ("priority_score", "monthly_frequency", "pipeline_enabled", "editorial_goal", "target_audience", "internal_notes"):
        if column_exists("categories", col):
            op.drop_column("categories", col)

    for col in ("ideas_per_week", "max_pending_drafts", "paused_until", "paused_indefinitely", "default_quality_mode", "category_strategy_json", "launch_hours"):
        if column_exists("project_pipelines", col):
            op.drop_column("project_pipelines", col)
