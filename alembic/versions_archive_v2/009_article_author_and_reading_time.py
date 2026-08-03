"""009 article author and reading time

Revision ID: 009
Revises: 008
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("author_name", sa.String(length=255), nullable=True))
    op.add_column("articles", sa.Column("reading_time_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "reading_time_minutes")
    op.drop_column("articles", "author_name")
