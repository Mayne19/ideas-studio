"""ensure_boolean_columns_articles

Revision ID: e0f2a4b6c8d0
Revises: d9e1f3a5b7c8
Create Date: 2026-07-04

Filet de sécurité pour PostgreSQL : les révisions précédentes
(4d6055864a7a, b7c9d1e2f3a4, d9e1f3a5b7c8) utilisaient le pattern
SAVEPOINT qui avale les erreurs — la conversion INTEGER -> BOOLEAN a pu
échouer en silence en production (cas avéré pour featured, bloquée par
son default INTEGER).

Cette révision inspecte le type réel des colonnes (équivalent
information_schema.columns) et ne convertit que ce qui est encore
INTEGER. Elle est bruyante : toute erreur fait échouer la migration au
lieu d'être avalée. Conversion non destructive :
NULL -> NULL, 0 -> false, toute valeur non nulle -> true.

Sur SQLite, no-op assumé : un Boolean y est stocké en INTEGER.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e0f2a4b6c8d0'
down_revision: Union[str, None] = 'd9e1f3a5b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOOLEAN_COLUMNS = ("needs_faq", "needs_images", "global_score_valid", "featured")


def _integer_columns(bind) -> list[str]:
    insp = sa.inspect(bind)
    cols = {c["name"]: c["type"] for c in insp.get_columns("articles")}
    return [
        name for name in BOOLEAN_COLUMNS
        if name in cols and "INT" in str(cols[name]).upper()
    ]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite : Boolean stocké en INTEGER, rien à convertir

    for col in _integer_columns(bind):
        # Un default INTEGER bloque le cast automatique : le retirer d'abord
        op.execute(sa.text(f"ALTER TABLE articles ALTER COLUMN {col} DROP DEFAULT"))
        op.alter_column(
            "articles",
            col,
            type_=sa.Boolean(),
            postgresql_using=f"CASE WHEN {col} IS NULL THEN NULL WHEN {col} = 0 THEN false ELSE true END",
        )
        if col == "featured":
            op.execute(sa.text("ALTER TABLE articles ALTER COLUMN featured SET DEFAULT false"))


def downgrade() -> None:
    # Volontairement no-op : les révisions précédentes portent déjà le
    # downgrade vers INTEGER ; celle-ci n'est qu'un filet de sécurité.
    pass
