"""add_agent_cost_and_reader_settings

Ajoute à ai.pipelines deux réglages de l'agent rédacteur, éditables dans le
CMS (Paramètres → Pipeline) :
- agent_max_cost_usd : arrêt dur du coût d'un article (dollars, facturation
  OpenRouter), 3,00 par défaut ;
- agent_reader_fallback : lecture de secours des pages par un lecteur externe
  quand la lecture directe échoue, activée par défaut.

Revision ID: v3_0011
Revises: v3_0010
Create Date: 2026-10-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v3_0011"
down_revision: Union[str, None] = "v3_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("agent_max_cost_usd", sa.Numeric(6, 2), nullable=False,
                                         server_default="3.00"), schema="ai")
    op.add_column("pipelines", sa.Column("agent_reader_fallback", sa.Boolean(), nullable=False,
                                         server_default=sa.true()), schema="ai")
    op.create_check_constraint("ck_pipelines_agent_max_cost_usd", "pipelines",
                               "agent_max_cost_usd > 0 AND agent_max_cost_usd <= 20", schema="ai")


def downgrade() -> None:
    op.drop_constraint("ck_pipelines_agent_max_cost_usd", "pipelines", schema="ai")
    op.drop_column("pipelines", "agent_reader_fallback", schema="ai")
    op.drop_column("pipelines", "agent_max_cost_usd", schema="ai")
