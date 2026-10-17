"""restore the publication score threshold

Revision ID: v3_0015
Revises: v3_0014
Create Date: 2026-10-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v3_0015"
down_revision: Union[str, None] = "v3_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipelines",
        sa.Column("min_publish_score", sa.SmallInteger(), nullable=False, server_default=sa.text("90")),
        schema="ai",
    )
    op.create_check_constraint(
        "pipelines_min_publish_score_range",
        "pipelines",
        "min_publish_score BETWEEN 85 AND 100",
        schema="ai",
    )


def downgrade() -> None:
    op.drop_constraint("pipelines_min_publish_score_range", "pipelines", schema="ai")
    op.drop_column("pipelines", "min_publish_score", schema="ai")
