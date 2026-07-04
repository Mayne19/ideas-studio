"""add_max_parallel_writing_jobs

Revision ID: f1a3b5c7d9e0
Revises: e0f2a4b6c8d0
Create Date: 2026-07-04

Limite de rédactions IA simultanées par projet (file de production).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'f1a3b5c7d9e0'
down_revision: Union[str, None] = 'e0f2a4b6c8d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("project_pipelines")}
    if "max_parallel_writing_jobs" not in cols:
        op.add_column("project_pipelines", sa.Column("max_parallel_writing_jobs", sa.Integer(), nullable=True))


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("project_pipelines")}
    if "max_parallel_writing_jobs" in cols:
        with op.batch_alter_table("project_pipelines") as batch:
            batch.drop_column("max_parallel_writing_jobs")
