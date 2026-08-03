"""add activity_logs table

Revision ID: 018_add_activity_logs
Revises: 017_add_user_avatar
Create Date: 2026-06-11 12:00:00.000000

"""
import sqlalchemy as sa
from app.core.alembic_helpers import (
    create_index_if_missing,
    create_table_if_missing,
    drop_index_if_exists,
    drop_table_if_exists,
)


revision = '018_add_activity_logs'
down_revision = '017_add_user_avatar'
branch_labels = None
depends_on = None


def upgrade():
    create_table_if_missing(
        'activity_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('user_name', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    create_index_if_missing('ix_activity_logs_project_id', 'activity_logs', ['project_id'])
    create_index_if_missing('ix_activity_logs_user_id', 'activity_logs', ['user_id'])


def downgrade():
    drop_index_if_exists('ix_activity_logs_user_id', 'activity_logs')
    drop_index_if_exists('ix_activity_logs_project_id', 'activity_logs')
    drop_table_if_exists('activity_logs')
