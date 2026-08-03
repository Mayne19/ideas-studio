"""add avatar_url to users

Revision ID: 017_add_user_avatar
Revises: 016_add_ai_provider_configs
Create Date: 2026-06-11 12:00:00.000000

"""
import sqlalchemy as sa
from app.core.alembic_helpers import add_column_if_missing, drop_column_if_exists


revision = "017_add_user_avatar"
down_revision = "016_add_ai_provider_configs"
branch_labels = None
depends_on = None


def upgrade():
    add_column_if_missing("users", sa.Column("avatar_url", sa.String(500), nullable=True))


def downgrade():
    drop_column_if_exists("users", "avatar_url")
