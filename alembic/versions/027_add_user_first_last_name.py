"""add first_name and last_name to users

Revision ID: 027
Revises: 026
Create Date: 2026-06-23
"""

import sqlalchemy as sa

from app.core.alembic_helpers import add_column_if_missing


revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column_if_missing("users", sa.Column("first_name", sa.String(255), nullable=True))
    add_column_if_missing("users", sa.Column("last_name", sa.String(255), nullable=True))


def downgrade() -> None:
    pass
