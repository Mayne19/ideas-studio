"""add pipeline settings and logs tables

Revision ID: 012
Revises: 011
Create Date: 2026-05-17 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_pipelines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("active_days", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("launch_hour", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("articles_per_week", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("category_priorities", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index("ix_project_pipelines_project_id", "project_pipelines", ["project_id"])

    op.create_table(
        "pipeline_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("ideas_generated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("articles_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_logs_project_id", "pipeline_logs", ["project_id"])


def downgrade():
    op.drop_table("pipeline_logs")
    op.drop_table("project_pipelines")
