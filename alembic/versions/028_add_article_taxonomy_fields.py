"""add article taxonomy fields

Revision ID: 028
Revises: 027
Create Date: 2026-06-26
"""

import sqlalchemy as sa

from app.core.alembic_helpers import add_column_if_missing, create_index_if_missing, drop_index_if_exists


revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    add_column_if_missing("articles", sa.Column("sub_niche", sa.String(255), nullable=True))
    add_column_if_missing("articles", sa.Column("featured", sa.Integer(), nullable=False, server_default="0"))
    create_index_if_missing("ix_articles_sub_niche", "articles", ["sub_niche"])
    create_index_if_missing("ix_articles_featured", "articles", ["featured"])


def downgrade() -> None:
    drop_index_if_exists("ix_articles_featured", "articles")
    drop_index_if_exists("ix_articles_sub_niche", "articles")
