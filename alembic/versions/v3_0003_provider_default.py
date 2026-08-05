"""add_provider_credential_is_default

Ajoute ai.provider_credentials.is_default : choix explicite de l'utilisateur
pour la clé utilisée par défaut par un projet (resolve_default_provider),
jamais déduit automatiquement — corrige un bug où plusieurs credentials
(ex: Anthropic + Gemini) pour le même projet étaient piochées sans ordre
défini (pas de ORDER BY), causant un comportement apparemment aléatoire
entre providers, y compris une clé périmée.

Un index unique partiel garantit au plus une ligne is_default=true par
projet (et une globale, project_id NULL). Pas de migration de données :
toutes les lignes existantes restent is_default=false, l'utilisateur doit
choisir explicitement — voir docstring du modèle ProviderCredential.

Revision ID: v3_0003
Revises: v3_0002
Create Date: 2026-08-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v3_0003"
down_revision: Union[str, None] = "v3_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("provider_credentials", schema="ai")}
    if "is_default" not in existing:
        op.add_column(
            "provider_credentials",
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
            schema="ai",
        )

    existing_indexes = {ix["name"] for ix in insp.get_indexes("provider_credentials", schema="ai")}
    if "provider_credentials_one_default_per_project" not in existing_indexes:
        op.create_index(
            "provider_credentials_one_default_per_project",
            "provider_credentials",
            ["project_id"],
            unique=True,
            schema="ai",
            postgresql_where=sa.text("is_default = true AND project_id IS NOT NULL"),
        )
    if "provider_credentials_one_default_global" not in existing_indexes:
        op.create_index(
            "provider_credentials_one_default_global",
            "provider_credentials",
            ["is_default"],
            unique=True,
            schema="ai",
            postgresql_where=sa.text("is_default = true AND project_id IS NULL"),
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing_indexes = {ix["name"] for ix in insp.get_indexes("provider_credentials", schema="ai")}
    if "provider_credentials_one_default_per_project" in existing_indexes:
        op.drop_index("provider_credentials_one_default_per_project", table_name="provider_credentials", schema="ai")
    if "provider_credentials_one_default_global" in existing_indexes:
        op.drop_index("provider_credentials_one_default_global", table_name="provider_credentials", schema="ai")

    existing = {c["name"] for c in insp.get_columns("provider_credentials", schema="ai")}
    if "is_default" in existing:
        with op.batch_alter_table("provider_credentials", schema="ai") as batch:
            batch.drop_column("is_default")
