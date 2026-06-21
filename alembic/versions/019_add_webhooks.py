"""add webhooks table

Revision ID: 019_add_webhooks
Revises: 018_add_activity_logs
Create Date: 2026-06-11 13:00:00.000000

"""
import sqlalchemy as sa
from app.core.alembic_helpers import (
    create_index_if_missing,
    create_table_if_missing,
    drop_index_if_exists,
    drop_table_if_exists,
)


revision = '019_add_webhooks'
down_revision = '018_add_activity_logs'
branch_labels = None
depends_on = None


def upgrade():
    create_table_if_missing(
        'webhooks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=2000), nullable=False),
        sa.Column('events', sa.Text(), nullable=False),
        sa.Column('secret', sa.String(length=128), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_triggered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_status', sa.String(length=50), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    create_index_if_missing('ix_webhooks_project_id', 'webhooks', ['project_id'])


def downgrade():
    drop_index_if_exists('ix_webhooks_project_id', 'webhooks')
    drop_table_if_exists('webhooks')
