"""add_writing_error_and_cancel

Revision ID: a5c7e9b1d3f5
Revises: f1a3b5c7d9e0
Create Date: 2026-07-04

writing_error : raison d'échec de rédaction visible dans l'UI.
writing_cancel_requested : demande d'annulation d'une rédaction en cours.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'a5c7e9b1d3f5'
down_revision: Union[str, None] = 'f1a3b5c7d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = (
    ("writing_error", sa.Text()),
    ("writing_cancel_requested", sa.Boolean()),
)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("articles")}
    for name, col_type in COLUMNS:
        if name not in existing:
            op.add_column("articles", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("articles")}
    for name, _ in COLUMNS:
        if name in existing:
            with op.batch_alter_table("articles") as batch:
                batch.drop_column(name)
