"""011 published article fields for draft/publish separation

Revision ID: 011
Revises: 010
Create Date: 2026-05-17
"""

from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("scheduled_update_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("articles", sa.Column("published_content", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("published_title", sa.String(length=500), nullable=True))
    op.add_column("articles", sa.Column("published_excerpt", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("published_meta_description", sa.String(length=500), nullable=True))
    op.add_column("articles", sa.Column("published_cover_image_url", sa.String(length=1000), nullable=True))
    op.add_column("articles", sa.Column("published_faq_json", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("published_callouts_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "scheduled_update_at")
    op.drop_column("articles", "published_content")
    op.drop_column("articles", "published_title")
    op.drop_column("articles", "published_excerpt")
    op.drop_column("articles", "published_meta_description")
    op.drop_column("articles", "published_cover_image_url")
    op.drop_column("articles", "published_faq_json")
    op.drop_column("articles", "published_callouts_json")
