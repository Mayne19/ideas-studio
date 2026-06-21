"""add kanban_columns table

Revision ID: dd3a273d4f33
Revises: 019_add_webhooks
Create Date: 2026-06-11 17:34:18.443792

"""
from typing import Sequence, Union
import sqlalchemy as sa
from app.core.alembic_helpers import (
    create_index_if_missing,
    create_table_if_missing,
    drop_index_if_exists,
    drop_table_if_exists,
)


revision: str = 'dd3a273d4f33'
down_revision: Union[str, None] = '019_add_webhooks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    create_table_if_missing(
        'kanban_columns',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'label', name='uq_kanban_column_label'),
    )
    create_index_if_missing('ix_kanban_columns_project_id', 'kanban_columns', ['project_id'])


def downgrade() -> None:
    drop_index_if_exists('ix_kanban_columns_project_id', 'kanban_columns')
    drop_table_if_exists('kanban_columns')
