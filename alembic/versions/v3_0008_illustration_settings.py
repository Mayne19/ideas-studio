"""add_illustration_settings

Ajoute ai.illustration_settings : mode des images d'illustration des
articles (ai | unsplash | none) et réglages du mode IA (modèle, style
visuel, couleurs de marque, nombre max d'images), éditables depuis le CMS
(Paramètres → Services externes). Une ligne par projet, project_id NULL =
défaut global.

Migration purement additive (nouvelle table + index) : aucune donnée
existante n'est touchée. Sans ligne, le code garde le comportement
historique (photos Unsplash si une clé est configurée).

Revision ID: v3_0008
Revises: v3_0007
Create Date: 2026-10-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v3_0008"
down_revision: Union[str, None] = "v3_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "illustration_settings"


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
            sa.Column("mode", sa.Text(), nullable=False, server_default=sa.text("'unsplash'")),
            sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            schema="ai",
        )

    insp = sa.inspect(op.get_bind())
    existing_indexes = {ix["name"] for ix in insp.get_indexes(TABLE, schema="ai")}
    if "illustration_settings_unique_project" not in existing_indexes:
        op.create_index(
            "illustration_settings_unique_project",
            TABLE,
            ["project_id"],
            unique=True,
            schema="ai",
            postgresql_where=sa.text("project_id IS NOT NULL"),
        )
    if "illustration_settings_unique_global" not in existing_indexes:
        # Une seule ligne globale : index unique sur une expression constante
        # restreint aux lignes project_id NULL.
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS illustration_settings_unique_global "
            "ON ai.illustration_settings ((project_id IS NULL)) WHERE project_id IS NULL"
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table(TABLE, schema="ai"):
        op.drop_table(TABLE, schema="ai")
