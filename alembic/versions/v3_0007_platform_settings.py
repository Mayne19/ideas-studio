"""add_platform_settings

Ajoute core.platform_settings : réglages globaux de l'instance (clé/valeur
JSONB), éditables par le compte staff depuis l'interface. Premier usage :
registration.open (inscription libre, fermée par défaut — sans invitation
valide, /auth/register refuse les nouveaux comptes, sauf le tout premier
compte qui initialise l'instance).

Migration purement additive (nouvelle table) : aucune donnée existante n'est
touchée. Absence de ligne = valeur par défaut côté code (inscription fermée).

Revision ID: v3_0007
Revises: v3_0006
Create Date: 2026-10-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v3_0007"
down_revision: Union[str, None] = "v3_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "platform_settings"


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(TABLE, schema="core"):
        op.create_table(
            TABLE,
            sa.Column("key", sa.Text(), primary_key=True),
            sa.Column("value", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column(
                "updated_by", postgresql.UUID(as_uuid=False),
                sa.ForeignKey("core.users.id", ondelete="SET NULL"), nullable=True,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            schema="core",
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table(TABLE, schema="core"):
        op.drop_table(TABLE, schema="core")
