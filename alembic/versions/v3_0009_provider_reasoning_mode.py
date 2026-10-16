"""add_provider_reasoning_mode

Ajoute ai.provider_credentials.reasoning_mode : raisonnement interne du
modèle ('off' | 'auto'), éditable depuis le CMS (Paramètres → Fournisseurs
IA). 'off' par défaut : deepseek-v4-flash raisonne sinon sur ~99 % des
tokens générés, ce qui tronquait les passes longues (cohérence, correction
de structure) à 16 384 tokens et multipliait coût et durée de rédaction.

Migration purement additive (colonne avec défaut).

Revision ID: v3_0009
Revises: v3_0008
Create Date: 2026-10-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v3_0009"
down_revision: Union[str, None] = "v3_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "provider_credentials",
        sa.Column("reasoning_mode", sa.Text(), nullable=False, server_default="off"),
        schema="ai",
    )
    op.create_check_constraint(
        "ck_provider_credentials_reasoning_mode",
        "provider_credentials",
        "reasoning_mode IN ('off', 'auto')",
        schema="ai",
    )


def downgrade() -> None:
    op.drop_constraint("ck_provider_credentials_reasoning_mode", "provider_credentials", schema="ai")
    op.drop_column("provider_credentials", "reasoning_mode", schema="ai")
