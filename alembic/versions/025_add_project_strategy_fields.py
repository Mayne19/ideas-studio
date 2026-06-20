"""add project strategy fields

Revision ID: 025
Revises: 024
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    columns = [
        ("timezone", sa.Column("timezone", sa.String(length=80), nullable=True)),
        ("description", sa.Column("description", sa.Text(), nullable=True)),
        ("industry", sa.Column("industry", sa.String(length=255), nullable=True)),
        ("reader_level", sa.Column("reader_level", sa.String(length=120), nullable=True)),
        ("writing_style", sa.Column("writing_style", sa.String(length=255), nullable=True)),
        ("editorial_goal", sa.Column("editorial_goal", sa.Text(), nullable=True)),
        ("value_proposition", sa.Column("value_proposition", sa.Text(), nullable=True)),
        ("allowed_topics", sa.Column("allowed_topics", sa.Text(), nullable=True)),
        ("forbidden_topics", sa.Column("forbidden_topics", sa.Text(), nullable=True)),
        ("words_to_avoid", sa.Column("words_to_avoid", sa.Text(), nullable=True)),
        ("average_target_length", sa.Column("average_target_length", sa.String(length=120), nullable=True)),
        ("preferred_formats", sa.Column("preferred_formats", sa.Text(), nullable=True)),
        ("technical_level", sa.Column("technical_level", sa.String(length=120), nullable=True)),
        ("seo_rules", sa.Column("seo_rules", sa.Text(), nullable=True)),
        ("geo_rules", sa.Column("geo_rules", sa.Text(), nullable=True)),
        ("source_guidelines", sa.Column("source_guidelines", sa.Text(), nullable=True)),
        ("internal_linking_guidelines", sa.Column("internal_linking_guidelines", sa.Text(), nullable=True)),
        ("external_linking_guidelines", sa.Column("external_linking_guidelines", sa.Text(), nullable=True)),
        ("style_examples", sa.Column("style_examples", sa.Text(), nullable=True)),
    ]
    for name, column in columns:
        if not _has_column("projects", name):
            op.add_column("projects", column)


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
        if _has_column("projects", name):
            op.drop_column("projects", name)
