"""Add cost_limit_per_article_eur to project_pipelines

Revision ID: 022
Revises: 021
Create Date: 2026-06-20 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '022'
down_revision: Union[str, None] = '021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('project_pipelines') as batch_op:
        batch_op.add_column(sa.Column('cost_limit_per_article_eur', sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('project_pipelines') as batch_op:
        batch_op.drop_column('cost_limit_per_article_eur')
