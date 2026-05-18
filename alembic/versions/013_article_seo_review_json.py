"""add article seo review json

Revision ID: 013_article_seo_review_json
Revises: 012_pipeline_settings
Create Date: 2026-05-18
"""

from alembic import op
import sqlalchemy as sa


revision = "013_article_seo_review_json"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("seo_review_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "seo_review_json")
