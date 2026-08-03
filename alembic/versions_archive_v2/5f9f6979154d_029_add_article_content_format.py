"""029_add_article_content_format

Revision ID: 5f9f6979154d
Revises: 028
Create Date: 2026-06-27 10:02:26.822260

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '5f9f6979154d'
down_revision: Union[str, None] = '028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('articles', sa.Column('content_format', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('articles', 'content_format')
