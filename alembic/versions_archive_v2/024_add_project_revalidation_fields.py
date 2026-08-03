"""add project revalidation fields

Revision ID: 024
Revises: 023
Create Date: 2026-06-20
"""

import sqlalchemy as sa
from app.core.alembic_helpers import add_column_if_missing, drop_column_if_exists


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = [
        sa.Column("public_site_url", sa.String(length=1000), nullable=True),
        sa.Column("revalidate_url", sa.String(length=1000), nullable=True),
        sa.Column("revalidate_secret_encrypted", sa.Text(), nullable=True),
        sa.Column("last_revalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_revalidate_status", sa.String(length=50), nullable=True),
        sa.Column("last_revalidate_error", sa.Text(), nullable=True),
    ]
    for column in columns:
        add_column_if_missing("projects", column)


def downgrade() -> None:
    for name in [
        "last_revalidate_error",
        "last_revalidate_status",
        "last_revalidated_at",
        "revalidate_secret_encrypted",
        "revalidate_url",
        "public_site_url",
    ]:
        drop_column_if_exists("projects", name)
