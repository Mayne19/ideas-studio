"""add_word_count_range

Revision ID: f3a1c2d4e5b6
Revises: 30d0f0f653d5
Create Date: 2026-07-02

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f3a1c2d4e5b6'
down_revision: Union[str, None] = '30d0f0f653d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("projects", "categories")
COLUMNS = ("word_count_min", "word_count_max")


def upgrade() -> None:
    # Idempotent : l'inspecteur remplace le "IF NOT EXISTS" (non supporté par SQLite)
    # et le pattern SAVEPOINT (qui ne persiste pas les DDL bruts sur SQLite).
    insp = sa.inspect(op.get_bind())
    for table in TABLES:
        existing = {c["name"] for c in insp.get_columns(table)}
        for col in COLUMNS:
            if col not in existing:
                op.add_column(table, sa.Column(col, sa.Integer(), nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for table in TABLES:
        existing = {c["name"] for c in insp.get_columns(table)}
        for col in COLUMNS:
            if col in existing:
                with op.batch_alter_table(table) as batch:
                    batch.drop_column(col)
