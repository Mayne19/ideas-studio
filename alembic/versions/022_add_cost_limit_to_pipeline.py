"""Add cost_limit_per_article_eur to project_pipelines

Revision ID: 022
Revises: 021
Create Date: 2026-06-20 14:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from app.core.alembic_helpers import add_column_if_missing, drop_column_if_exists


revision: str = '022'
down_revision: Union[str, None] = '021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing('project_pipelines', sa.Column('cost_limit_per_article_eur', sa.Float(), nullable=True))


def downgrade() -> None:
    drop_column_if_exists('project_pipelines', 'cost_limit_per_article_eur')
