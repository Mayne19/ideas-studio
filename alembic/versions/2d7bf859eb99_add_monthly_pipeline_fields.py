"""add_monthly_pipeline_fields

Revision ID: 2d7bf859eb99
Revises: eb654f66829e
Create Date: 2026-07-01 22:24:40.629331

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = '2d7bf859eb99'
down_revision: Union[str, None] = 'eb654f66829e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('project_pipelines') as batch_op:
        batch_op.add_column(sa.Column('ideas_day_of_month', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('publish_hour_start', sa.Integer(), nullable=True, server_default='8'))
        batch_op.add_column(sa.Column('publish_hour_end', sa.Integer(), nullable=True, server_default='10'))


def downgrade() -> None:
    with op.batch_alter_table('project_pipelines') as batch_op:
        batch_op.drop_column('publish_hour_end')
        batch_op.drop_column('publish_hour_start')
        batch_op.drop_column('ideas_day_of_month')
