"""add_agent_reasoning_and_review_settings

Ajoute à ai.pipelines deux réglages de l'agent rédacteur, éditables dans le
CMS (Paramètres → Pipeline) :
- agent_reasoning_effort : effort de raisonnement du modèle (low, medium,
  high), « low » par défaut ;
- agent_consistency_review : relecture de cohérence indépendante après la
  rédaction (contradictions entre le calcul de l'article et le tableau, les
  conseils et la conclusion), désactivée par défaut.

Revision ID: v3_0012
Revises: v3_0011
Create Date: 2026-10-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v3_0012"
down_revision: Union[str, None] = "v3_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("agent_reasoning_effort", sa.Text(), nullable=False, server_default="low"),
                  schema="ai")
    op.add_column("pipelines", sa.Column("agent_consistency_review", sa.Boolean(), nullable=False,
                                         server_default=sa.false()), schema="ai")
    op.create_check_constraint("ck_pipelines_agent_reasoning_effort", "pipelines",
                               "agent_reasoning_effort IN ('low', 'medium', 'high')", schema="ai")


def downgrade() -> None:
    op.drop_constraint("ck_pipelines_agent_reasoning_effort", "pipelines", schema="ai")
    op.drop_column("pipelines", "agent_consistency_review", schema="ai")
    op.drop_column("pipelines", "agent_reasoning_effort", schema="ai")
