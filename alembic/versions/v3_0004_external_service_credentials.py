"""add_external_service_credentials

Ajoute ai.external_service_credentials : clés des services externes non-IA
(recherche web : serper/brave/serpapi/google_cse ; images : unsplash/brave),
chiffrées, éditables depuis le CMS (Paramètres → Services externes) au lieu
des seules variables d'environnement. Une ligne par (projet, service),
project_id NULL = défaut global.

Migration purement additive (nouvelle table + index) : aucune donnée
existante n'est touchée. Les variables d'environnement (SERPER_API_KEY, ...)
restent le repli quand aucune ligne n'est configurée.

Revision ID: v3_0004
Revises: v3_0003
Create Date: 2026-10-15

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v3_0004"
down_revision: Union[str, None] = "v3_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "external_service_credentials"


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(TABLE, schema="ai"):
        op.create_table(
            TABLE,
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "project_id", postgresql.UUID(as_uuid=False),
                sa.ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=True,
            ),
            sa.Column("service", sa.Text(), nullable=False),
            sa.Column("provider", sa.Text(), nullable=False),
            sa.Column("secret_ref", sa.Text(), nullable=False),
            sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_test_ok", sa.Boolean(), nullable=True),
            sa.Column("last_test_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            schema="ai",
        )

    # Nouvel inspecteur : celui du dessus a pu mettre en cache l'absence de
    # la table avant sa création.
    insp = sa.inspect(op.get_bind())
    existing_indexes = {ix["name"] for ix in insp.get_indexes(TABLE, schema="ai")}
    if "external_service_credentials_unique_project" not in existing_indexes:
        op.create_index(
            "external_service_credentials_unique_project",
            TABLE,
            ["project_id", "service"],
            unique=True,
            schema="ai",
            postgresql_where=sa.text("project_id IS NOT NULL"),
        )
    if "external_service_credentials_unique_global" not in existing_indexes:
        op.create_index(
            "external_service_credentials_unique_global",
            TABLE,
            ["service"],
            unique=True,
            schema="ai",
            postgresql_where=sa.text("project_id IS NULL"),
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table(TABLE, schema="ai"):
        op.drop_table(TABLE, schema="ai")
