"""add kanban_columns table

Revision ID: dd3a273d4f33
Revises: 019_add_webhooks
Create Date: 2026-06-11 17:34:18.443792

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'dd3a273d4f33'
down_revision: Union[str, None] = '019_add_webhooks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('kanban_columns',
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
    sa.UniqueConstraint('project_id', 'label', name='uq_kanban_column_label')
    )
    op.create_index(op.f('ix_kanban_columns_project_id'), 'kanban_columns', ['project_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_kanban_columns_project_id'), table_name='kanban_columns')
    op.drop_table('kanban_columns')
