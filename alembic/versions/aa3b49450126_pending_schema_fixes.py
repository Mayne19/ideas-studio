"""pending_schema_fixes

Revision ID: aa3b49450126
Revises: 5ac6925c87bc
Create Date: 2026-06-29 07:18:44.046416

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'aa3b49450126'
down_revision: Union[str, None] = '5ac6925c87bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_project_agent_assignment', 'agent_assignments', ['project_id', 'agent_id'])
    op.create_unique_constraint('uq_project_provider', 'ai_provider_configs', ['project_id', 'provider'])
    op.create_foreign_key(None, 'articles', 'articles', ['original_article_id'], ['id'])
    op.create_foreign_key(None, 'articles', 'articles', ['revision_of_article_id'], ['id'])
    op.add_column('notifications', sa.Column('link', sa.String(length=1000), nullable=True))
    op.create_unique_constraint(None, 'users', ['username'])


def downgrade() -> None:
    op.drop_constraint(None, 'users', type_='unique')
    op.drop_column('notifications', 'link')
    op.drop_constraint(None, 'articles', type_='foreignkey')
    op.drop_constraint(None, 'articles', type_='foreignkey')
    op.drop_constraint('uq_project_provider', 'ai_provider_configs', type_='unique')
    op.drop_constraint('uq_project_agent_assignment', 'agent_assignments', type_='unique')
