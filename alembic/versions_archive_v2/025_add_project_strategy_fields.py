"""add project strategy fields

Revision ID: 025
Revises: 024
Create Date: 2026-06-20
"""

import sqlalchemy as sa
from app.core.alembic_helpers import add_column_if_missing, drop_column_if_exists


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = [
        sa.Column("timezone", sa.String(length=80), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("reader_level", sa.String(length=120), nullable=True),
        sa.Column("writing_style", sa.String(length=255), nullable=True),
        sa.Column("editorial_goal", sa.Text(), nullable=True),
        sa.Column("value_proposition", sa.Text(), nullable=True),
        sa.Column("allowed_topics", sa.Text(), nullable=True),
        sa.Column("forbidden_topics", sa.Text(), nullable=True),
        sa.Column("words_to_avoid", sa.Text(), nullable=True),
        sa.Column("average_target_length", sa.String(length=120), nullable=True),
        sa.Column("preferred_formats", sa.Text(), nullable=True),
        sa.Column("technical_level", sa.String(length=120), nullable=True),
        sa.Column("seo_rules", sa.Text(), nullable=True),
        sa.Column("geo_rules", sa.Text(), nullable=True),
        sa.Column("source_guidelines", sa.Text(), nullable=True),
        sa.Column("internal_linking_guidelines", sa.Text(), nullable=True),
        sa.Column("external_linking_guidelines", sa.Text(), nullable=True),
        sa.Column("style_examples", sa.Text(), nullable=True),
    ]
    for column in columns:
        add_column_if_missing("projects", column)


def downgrade() -> None:
    for name in [
        "style_examples",
        "external_linking_guidelines",
        "internal_linking_guidelines",
        "source_guidelines",
        "geo_rules",
        "seo_rules",
        "technical_level",
        "preferred_formats",
        "average_target_length",
        "words_to_avoid",
        "forbidden_topics",
        "allowed_topics",
        "value_proposition",
        "editorial_goal",
        "writing_style",
        "reader_level",
        "industry",
        "description",
        "timezone",
    ]:
        drop_column_if_exists("projects", name)
