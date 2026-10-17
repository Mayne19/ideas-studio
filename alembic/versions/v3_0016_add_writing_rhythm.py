"""add daily writing capacity

Revision ID: v3_0016
Revises: v3_0015
Create Date: 2026-10-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v3_0016"
down_revision: Union[str, None] = "v3_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipelines",
        sa.Column("articles_per_day", sa.SmallInteger(), nullable=False, server_default=sa.text("2")),
        schema="ai",
    )


def downgrade() -> None:
    op.drop_column("pipelines", "articles_per_day", schema="ai")
