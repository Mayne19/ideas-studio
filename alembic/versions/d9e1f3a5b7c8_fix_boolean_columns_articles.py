"""fix_boolean_columns_articles

Revision ID: d9e1f3a5b7c8
Revises: b7c9d1e2f3a4
Create Date: 2026-07-04

Convertit needs_faq, needs_images (créées INTEGER par 245d2dd9956a) et
global_score_valid (créée INTEGER par 023) vers BOOLEAN, pour aligner la
base PostgreSQL sur le modèle SQLAlchemy (Mapped[bool | None]) — sinon
psycopg2 lève DatatypeMismatch à l'insertion de True/False.

Non destructif : USING col::boolean convertit 0 -> false, 1 -> true,
NULL -> NULL. DROP DEFAULT défensif avant le cast (PostgreSQL refuse le
cast automatique d'un default INTEGER). Sur SQLite, ALTER COLUMN TYPE
n'est pas supporté : chaque étape échoue dans son SAVEPOINT et la
colonne reste INTEGER, stockage normal d'un Boolean SQLite.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'd9e1f3a5b7c8'
down_revision: Union[str, None] = 'b7c9d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNS = ("needs_faq", "needs_images", "global_score_valid")


def _safe(conn):
    def run(sql: str):
        conn.execute(sa.text("SAVEPOINT sp"))
        try:
            conn.execute(sa.text(sql))
            conn.execute(sa.text("RELEASE SAVEPOINT sp"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp"))
    return run


def upgrade() -> None:
    safe = _safe(op.get_bind())
    for col in COLUMNS:
        safe(f"ALTER TABLE articles ALTER COLUMN {col} DROP DEFAULT")
        safe(f"ALTER TABLE articles ALTER COLUMN {col} TYPE BOOLEAN USING {col}::boolean")


def downgrade() -> None:
    safe = _safe(op.get_bind())
    for col in COLUMNS:
        safe(
            f"ALTER TABLE articles ALTER COLUMN {col} TYPE INTEGER "
            f"USING CASE WHEN {col} IS NULL THEN NULL WHEN {col} THEN 1 ELSE 0 END"
        )
