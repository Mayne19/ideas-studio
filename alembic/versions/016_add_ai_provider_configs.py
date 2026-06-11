"""add ai_provider_configs table

Revision ID: 016_add_ai_provider_configs
Revises: 015_add_article_comments
Create Date: 2026-06-11 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '016_add_ai_provider_configs'
down_revision = '015_add_article_comments'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_provider_configs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('last_test_status', sa.String(length=50), nullable=True),
        sa.Column('last_test_error', sa.Text(), nullable=True),
        sa.Column('last_tested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_provider_configs_provider'), 'ai_provider_configs', ['provider'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_ai_provider_configs_provider'), table_name='ai_provider_configs')
    op.drop_table('ai_provider_configs')
