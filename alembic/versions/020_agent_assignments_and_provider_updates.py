"""Add agent_assignments, ai_usage_logs, update ai_provider_configs

Revision ID: 020
Revises: dd3a273d4f33
Create Date: 2026-06-11 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.core.alembic_helpers import (
    add_column_if_missing,
    create_index_if_missing,
    create_table_if_missing,
    drop_column_if_exists,
    drop_index_if_exists,
    drop_table_if_exists,
    table_exists,
    unique_constraint_exists,
)


revision: str = '020'
down_revision: Union[str, None] = 'dd3a273d4f33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── agent_assignments table ────────────────────────────────────────
    create_table_if_missing(
        'agent_assignments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=True),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('provider_id', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('priority', sa.Integer(), nullable=False, server_default="0"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'agent_id', name='uq_project_agent_assignment'),
    )
    create_index_if_missing('ix_agent_assignments_project_id', 'agent_assignments', ['project_id'])
    create_index_if_missing('ix_agent_assignments_agent_id', 'agent_assignments', ['agent_id'])

    # ── ai_usage_logs table ────────────────────────────────────────────
    create_table_if_missing(
        'ai_usage_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('provider_id', sa.String(), nullable=True),
        sa.Column('provider_name', sa.String(length=50), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('project_id', sa.String(), nullable=True),
        sa.Column('article_id', sa.String(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default="success"),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    create_index_if_missing('ix_ai_usage_logs_agent_id', 'ai_usage_logs', ['agent_id'])
    create_index_if_missing('ix_ai_usage_logs_project_id', 'ai_usage_logs', ['project_id'])

    # ── Update ai_provider_configs ─────────────────────────────────────
    add_column_if_missing('ai_provider_configs', sa.Column('project_id', sa.String(), nullable=True))
    add_column_if_missing('ai_provider_configs', sa.Column('display_name', sa.String(length=100), nullable=True))
    create_index_if_missing('ix_ai_provider_configs_project_id', 'ai_provider_configs', ['project_id'])

    # Drop the old unique index on provider, create non-unique
    drop_index_if_exists('ix_ai_provider_configs_provider', 'ai_provider_configs')
    create_index_if_missing('ix_ai_provider_configs_provider', 'ai_provider_configs', ['provider'])

    # Add unique constraint on (project_id, provider). Batch mode keeps SQLite fresh installs working.
    if table_exists('ai_provider_configs') and not unique_constraint_exists('ai_provider_configs', 'uq_project_provider'):
        with op.batch_alter_table('ai_provider_configs') as batch_op:
            batch_op.create_unique_constraint('uq_project_provider', ['project_id', 'provider'])


def downgrade() -> None:
    if table_exists('ai_provider_configs') and unique_constraint_exists('ai_provider_configs', 'uq_project_provider'):
        with op.batch_alter_table('ai_provider_configs') as batch_op:
            batch_op.drop_constraint('uq_project_provider', type_='unique')
    drop_index_if_exists('ix_ai_provider_configs_provider', 'ai_provider_configs')
    create_index_if_missing('ix_ai_provider_configs_provider', 'ai_provider_configs', ['provider'], unique=True)
    drop_index_if_exists('ix_ai_provider_configs_project_id', 'ai_provider_configs')
    drop_column_if_exists('ai_provider_configs', 'display_name')
    drop_column_if_exists('ai_provider_configs', 'project_id')
    drop_index_if_exists('ix_ai_usage_logs_project_id', 'ai_usage_logs')
    drop_index_if_exists('ix_ai_usage_logs_agent_id', 'ai_usage_logs')
    drop_table_if_exists('ai_usage_logs')
    drop_index_if_exists('ix_agent_assignments_agent_id', 'agent_assignments')
    drop_index_if_exists('ix_agent_assignments_project_id', 'agent_assignments')
    drop_table_if_exists('agent_assignments')
