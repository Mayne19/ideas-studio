"""007 category colors

Revision ID: 007
Revises: 006
Create Date: 2026-05-11
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("color", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "color")
