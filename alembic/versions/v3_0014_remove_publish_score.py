"""remove the obsolete publication score threshold

The editorial workflow validates its three technical checks and requires a
human decision. It no longer stores or evaluates a publication score.

Revision ID: v3_0014
Revises: v3_0013
Create Date: 2026-10-17

"""
from typing import Sequence, Union

from alembic import op


revision: str = "v3_0014"
down_revision: Union[str, None] = "v3_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("pipelines_min_publish_score_range", "pipelines", schema="ai")
    op.drop_column("pipelines", "min_publish_score", schema="ai")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column("pipelines", sa.Column("min_publish_score", sa.SmallInteger(), nullable=False, server_default=sa.text("90")), schema="ai")
    op.create_check_constraint(
        "pipelines_min_publish_score_range",
        "pipelines",
        "min_publish_score BETWEEN 85 AND 100",
        schema="ai",
    )
