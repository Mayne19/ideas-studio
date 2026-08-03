"""010 project callout templates

Revision ID: 010
Revises: 009
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_callout_templates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("style", sa.String(length=100), nullable=True),
        sa.Column("default_title", sa.String(length=255), nullable=True),
        sa.Column("color_background", sa.String(length=20), nullable=True),
        sa.Column("color_border", sa.String(length=20), nullable=True),
        sa.Column("color_text", sa.String(length=20), nullable=True),
        sa.Column("icon", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("class_name", sa.String(length=255), nullable=True),
        sa.Column("settings_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_callout_templates_project_id"), "project_callout_templates", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_callout_templates_slug"), "project_callout_templates", ["slug"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_project_callout_templates_slug"), table_name="project_callout_templates")
    op.drop_index(op.f("ix_project_callout_templates_project_id"), table_name="project_callout_templates")
    op.drop_table("project_callout_templates")
