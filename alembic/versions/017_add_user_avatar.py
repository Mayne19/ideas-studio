"""add avatar_url to users

Revision ID: 017_add_user_avatar
Revises: 016_add_ai_provider_configs
Create Date: 2026-06-11 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "017_add_user_avatar"
down_revision = "016_add_ai_provider_configs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))


def downgrade():
    op.drop_column("users", "avatar_url")
