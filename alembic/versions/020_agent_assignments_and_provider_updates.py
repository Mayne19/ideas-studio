"""Add agent_assignments, ai_usage_logs, update ai_provider_configs

Revision ID: 020
Revises: dd3a273d4f33
Create Date: 2026-06-11 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '020'
down_revision: Union[str, None] = 'dd3a273d4f33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── agent_assignments table ────────────────────────────────────────
    op.create_table(
        'agent_assignments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=True),
        sa.Column('agent_id', sa.String(length=100), nullable=False),
        sa.Column('provider_id', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('priority', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'agent_id', name='uq_project_agent_assignment'),
    )
    op.create_index(op.f('ix_agent_assignments_project_id'), 'agent_assignments', ['project_id'], unique=False)
    op.create_index(op.f('ix_agent_assignments_agent_id'), 'agent_assignments', ['agent_id'], unique=False)

    # ── ai_usage_logs table ────────────────────────────────────────────
    op.create_table(
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
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'success'")),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_usage_logs_agent_id'), 'ai_usage_logs', ['agent_id'], unique=False)
    op.create_index(op.f('ix_ai_usage_logs_project_id'), 'ai_usage_logs', ['project_id'], unique=False)

    # ── Update ai_provider_configs ─────────────────────────────────────
    op.add_column('ai_provider_configs', sa.Column('project_id', sa.String(), nullable=True))
    op.add_column('ai_provider_configs', sa.Column('display_name', sa.String(length=100), nullable=True))
    op.create_index(op.f('ix_ai_provider_configs_project_id'), 'ai_provider_configs', ['project_id'], unique=False)

    # Drop the old unique index on provider, create non-unique
    op.drop_index('ix_ai_provider_configs_provider', table_name='ai_provider_configs')
    op.create_index(op.f('ix_ai_provider_configs_provider'), 'ai_provider_configs', ['provider'], unique=False)

    # Add unique constraint on (project_id, provider). Batch mode keeps SQLite fresh installs working.
    with op.batch_alter_table('ai_provider_configs') as batch_op:
        batch_op.create_unique_constraint('uq_project_provider', ['project_id', 'provider'])


def downgrade() -> None:
    with op.batch_alter_table('ai_provider_configs') as batch_op:
        batch_op.drop_constraint('uq_project_provider', type_='unique')
    op.drop_index(op.f('ix_ai_provider_configs_provider'), table_name='ai_provider_configs')
    op.create_index('ix_ai_provider_configs_provider', 'ai_provider_configs', ['provider'], unique=True)
    op.drop_index(op.f('ix_ai_provider_configs_project_id'), table_name='ai_provider_configs')
    op.drop_column('ai_provider_configs', 'display_name')
    op.drop_column('ai_provider_configs', 'project_id')
    op.drop_index(op.f('ix_ai_usage_logs_project_id'), table_name='ai_usage_logs')
    op.drop_index(op.f('ix_ai_usage_logs_agent_id'), table_name='ai_usage_logs')
    op.drop_table('ai_usage_logs')
    op.drop_index(op.f('ix_agent_assignments_agent_id'), table_name='agent_assignments')
    op.drop_index(op.f('ix_agent_assignments_project_id'), table_name='agent_assignments')
    op.drop_table('agent_assignments')
