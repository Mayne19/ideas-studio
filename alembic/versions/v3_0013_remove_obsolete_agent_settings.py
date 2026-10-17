"""remove obsolete agent pipeline settings

The local writer fixes its reader fallback and reasoning behavior in code.
These project-level switches are no longer part of the simplified workflow.

Revision ID: v3_0013
Revises: v3_0012
Create Date: 2026-10-17

"""
from typing import Sequence, Union

from alembic import op


revision: str = "v3_0013"
down_revision: Union[str, None] = "v3_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_pipelines_agent_reasoning_effort", "pipelines", schema="ai")
    op.drop_column("pipelines", "agent_consistency_review", schema="ai")
    op.drop_column("pipelines", "agent_reasoning_effort", schema="ai")
    op.drop_column("pipelines", "agent_reader_fallback", schema="ai")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column("pipelines", sa.Column("agent_reader_fallback", sa.Boolean(), nullable=False, server_default=sa.true()), schema="ai")
    op.add_column("pipelines", sa.Column("agent_reasoning_effort", sa.Text(), nullable=False, server_default="low"), schema="ai")
    op.add_column("pipelines", sa.Column("agent_consistency_review", sa.Boolean(), nullable=False, server_default=sa.false()), schema="ai")
    op.create_check_constraint(
        "ck_pipelines_agent_reasoning_effort",
        "pipelines",
        "agent_reasoning_effort IN ('low', 'medium', 'high')",
        schema="ai",
    )
