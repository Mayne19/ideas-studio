"""Add validation score and editorial date fields

Revision ID: 023
Revises: 022
Create Date: 2026-06-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table: str, column: str) -> bool:
    inspector = inspect(op.get_bind())
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        if not column_exists("articles", "global_score"):
            batch_op.add_column(sa.Column("global_score", sa.Float(), nullable=True))
        if not column_exists("articles", "global_score_valid"):
            batch_op.add_column(sa.Column("global_score_valid", sa.Integer(), nullable=True))
        if not column_exists("articles", "idea_generated_at"):
            batch_op.add_column(sa.Column("idea_generated_at", sa.DateTime(timezone=True), nullable=True))
        if not column_exists("articles", "idea_validated_at"):
            batch_op.add_column(sa.Column("idea_validated_at", sa.DateTime(timezone=True), nullable=True))
        if not column_exists("articles", "human_validated_at"):
            batch_op.add_column(sa.Column("human_validated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        for column in (
            "human_validated_at",
            "idea_validated_at",
            "idea_generated_at",
            "global_score_valid",
            "global_score",
        ):
            if column_exists("articles", column):
                batch_op.drop_column(column)
