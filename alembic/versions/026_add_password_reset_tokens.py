"""add password reset tokens

Revision ID: 026
Revises: 025
Create Date: 2026-06-21
"""

import sqlalchemy as sa

from app.core.alembic_helpers import (
    create_index_if_missing,
    create_table_if_missing,
    drop_index_if_exists,
    drop_table_if_exists,
)


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    create_table_if_missing(
        "password_reset_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    create_index_if_missing("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    create_index_if_missing("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    drop_index_if_exists("ix_password_reset_tokens_token_hash", "password_reset_tokens")
    drop_index_if_exists("ix_password_reset_tokens_user_id", "password_reset_tokens")
    drop_table_if_exists("password_reset_tokens")
