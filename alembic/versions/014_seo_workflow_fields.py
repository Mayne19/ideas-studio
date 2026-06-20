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


def table_exists(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    if not table_exists(table_name):
        return False
    inspector = inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if table_exists(table_name) and not column_exists(table_name, column.name):
        op.add_column(table_name, column)


def drop_column_if_exists(table_name: str, column_name: str) -> None:
    if table_exists(table_name) and column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)


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
        add_column_if_missing("articles", sa.Column(col, sa.JSON(), nullable=True))

    # Category extra fields
    add_column_if_missing("categories", sa.Column("priority_score", sa.Float(), nullable=True))
    add_column_if_missing("categories", sa.Column("monthly_frequency", sa.Integer(), nullable=True))
    add_column_if_missing("categories", sa.Column("pipeline_enabled", sa.Boolean(), nullable=True, server_default=sa.true()))
    add_column_if_missing("categories", sa.Column("editorial_goal", sa.Text(), nullable=True))
    add_column_if_missing("categories", sa.Column("target_audience", sa.Text(), nullable=True))
    add_column_if_missing("categories", sa.Column("internal_notes", sa.Text(), nullable=True))

    # Pipeline extra fields
    add_column_if_missing("project_pipelines", sa.Column("ideas_per_week", sa.Integer(), nullable=True, server_default="5"))
    add_column_if_missing("project_pipelines", sa.Column("max_pending_drafts", sa.Integer(), nullable=True, server_default="10"))
    add_column_if_missing("project_pipelines", sa.Column("paused_until", sa.DateTime(timezone=True), nullable=True))
    add_column_if_missing("project_pipelines", sa.Column("paused_indefinitely", sa.Boolean(), nullable=True, server_default=sa.false()))
    add_column_if_missing("project_pipelines", sa.Column("default_quality_mode", sa.String(20), nullable=True, server_default="quality"))
    add_column_if_missing("project_pipelines", sa.Column("category_strategy_json", sa.JSON(), nullable=True))
    add_column_if_missing("project_pipelines", sa.Column("launch_hours", sa.Text(), nullable=True))


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
        drop_column_if_exists("articles", col)

    for col in ("priority_score", "monthly_frequency", "pipeline_enabled", "editorial_goal", "target_audience", "internal_notes"):
        drop_column_if_exists("categories", col)

    for col in ("ideas_per_week", "max_pending_drafts", "paused_until", "paused_indefinitely", "default_quality_mode", "category_strategy_json", "launch_hours"):
        drop_column_if_exists("project_pipelines", col)
