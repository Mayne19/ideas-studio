"""add_pipeline_generation_mode

Ajoute ai.pipelines.generation_mode : « agent » (agent rédacteur unique,
docs/AGENT-WRITER-PROMPT.md) ou « pipeline » (ancienne chaîne, gardée pour
comparaison). Éditable dans le CMS (Paramètres → Pipeline). Défaut : agent.

Revision ID: v3_0010
Revises: v3_0009
Create Date: 2026-10-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v3_0010"
down_revision: Union[str, None] = "v3_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("generation_mode", sa.Text(), nullable=False, server_default="agent"),
                  schema="ai")
    op.create_check_constraint("ck_pipelines_generation_mode", "pipelines",
                               "generation_mode IN ('agent', 'pipeline')", schema="ai")


def downgrade() -> None:
    op.drop_constraint("ck_pipelines_generation_mode", "pipelines", schema="ai")
    op.drop_column("pipelines", "generation_mode", schema="ai")
