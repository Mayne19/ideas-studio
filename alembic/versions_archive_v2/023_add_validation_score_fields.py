"""Add validation score and editorial date fields

Revision ID: 023
Revises: 022
Create Date: 2026-06-20 16:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from app.core.alembic_helpers import add_column_if_missing, column_exists, drop_column_if_exists


revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("articles", sa.Column("global_score", sa.Float(), nullable=True))
    add_column_if_missing("articles", sa.Column("global_score_valid", sa.Integer(), nullable=True))
    add_column_if_missing("articles", sa.Column("idea_generated_at", sa.DateTime(timezone=True), nullable=True))
    add_column_if_missing("articles", sa.Column("idea_validated_at", sa.DateTime(timezone=True), nullable=True))
    add_column_if_missing("articles", sa.Column("human_validated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in (
        "human_validated_at",
        "idea_validated_at",
        "idea_generated_at",
        "global_score_valid",
        "global_score",
    ):
        if column_exists("articles", column):
            drop_column_if_exists("articles", column)
