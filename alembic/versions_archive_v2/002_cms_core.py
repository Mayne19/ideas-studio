"""cms core

Revision ID: 002
Revises: 001
Create Date: 2026-05-05
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("target_frequency", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "slug", name="uq_category_slug"),
    )
    op.create_index("ix_categories_project_id", "categories", ["project_id"])

    op.create_table(
        "articles",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("category_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("keyword", sa.String(255), nullable=True),
        sa.Column("secondary_keywords_json", sa.Text(), nullable=True),
        sa.Column("audience", sa.String(500), nullable=True),
        sa.Column("angle", sa.String(500), nullable=True),
        sa.Column("search_intent", sa.String(100), nullable=True),
        sa.Column("outline_json", sa.Text(), nullable=True),
        sa.Column("serp_summary_json", sa.Text(), nullable=True),
        sa.Column("opportunity_score", sa.Float(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("meta_title", sa.String(255), nullable=True),
        sa.Column("meta_description", sa.String(500), nullable=True),
        sa.Column("cover_image_url", sa.String(1000), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("seo_score", sa.Float(), nullable=True),
        sa.Column("readability_score", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("eeat_score", sa.Float(), nullable=True),
        sa.Column("readiness_status", sa.String(50), nullable=True),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
        sa.Column("rejection_note", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_articles_project_id", "articles", ["project_id"])
    op.create_index("ix_articles_status", "articles", ["status"])

    op.create_table(
        "traffic_events",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("path", sa.String(1000), nullable=True),
        sa.Column("referrer", sa.String(2000), nullable=True),
        sa.Column("country", sa.String(10), nullable=True),
        sa.Column("device", sa.String(20), nullable=True),
        sa.Column("browser", sa.String(50), nullable=True),
        sa.Column("visitor_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_traffic_events_project_id", "traffic_events", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_traffic_events_project_id", table_name="traffic_events")
    op.drop_table("traffic_events")
    op.drop_index("ix_articles_status", table_name="articles")
    op.drop_index("ix_articles_project_id", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_categories_project_id", table_name="categories")
    op.drop_table("categories")
