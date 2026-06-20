"""add project revalidation fields

Revision ID: 024
Revises: 023
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    columns = [
        ("public_site_url", sa.Column("public_site_url", sa.String(length=1000), nullable=True)),
        ("revalidate_url", sa.Column("revalidate_url", sa.String(length=1000), nullable=True)),
        ("revalidate_secret_encrypted", sa.Column("revalidate_secret_encrypted", sa.Text(), nullable=True)),
        ("last_revalidated_at", sa.Column("last_revalidated_at", sa.DateTime(timezone=True), nullable=True)),
        ("last_revalidate_status", sa.Column("last_revalidate_status", sa.String(length=50), nullable=True)),
        ("last_revalidate_error", sa.Column("last_revalidate_error", sa.Text(), nullable=True)),
    ]
    for name, column in columns:
        if not _has_column("projects", name):
            op.add_column("projects", column)


def downgrade() -> None:
    for name in [
        "last_revalidate_error",
        "last_revalidate_status",
        "last_revalidated_at",
        "revalidate_secret_encrypted",
        "revalidate_url",
        "public_site_url",
    ]:
        if _has_column("projects", name):
            op.drop_column("projects", name)
