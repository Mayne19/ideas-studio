"""add_human_insights_json_to_articles

Revision ID: 30d0f0f653d5
Revises: 2d7bf859eb99
Create Date: 2026-07-02 01:21:56.191033

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '30d0f0f653d5'
down_revision: Union[str, None] = '2d7bf859eb99'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('articles') as batch_op:
        batch_op.add_column(sa.Column('human_insights_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('articles') as batch_op:
        batch_op.drop_column('human_insights_json')
