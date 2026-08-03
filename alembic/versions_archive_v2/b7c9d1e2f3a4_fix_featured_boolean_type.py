"""fix_featured_boolean_type

Revision ID: b7c9d1e2f3a4
Revises: f3a1c2d4e5b6
Create Date: 2026-07-03

La révision 4d6055864a7a tentait déjà ce cast, mais PostgreSQL refuse
ALTER TYPE BOOLEAN tant que le default INTEGER '0' (posé par la révision
028) existe — l'erreur était avalée par le SAVEPOINT. Il faut donc
retirer le default, caster, puis reposer un default booléen.
Sur SQLite, ALTER COLUMN TYPE n'est pas supporté : chaque étape échoue
dans son SAVEPOINT et la colonne reste INTEGER, ce qui est le stockage
normal d'un Boolean SQLite.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b7c9d1e2f3a4'
down_revision: Union[str, None] = 'f3a1c2d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    def safe(sql: str):
        conn.execute(sa.text("SAVEPOINT sp"))
        try:
            conn.execute(sa.text(sql))
            conn.execute(sa.text("RELEASE SAVEPOINT sp"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp"))

    safe("ALTER TABLE articles ALTER COLUMN featured DROP DEFAULT")
    safe("ALTER TABLE articles ALTER COLUMN featured TYPE BOOLEAN USING featured::boolean")
    safe("ALTER TABLE articles ALTER COLUMN featured SET DEFAULT false")


def downgrade() -> None:
    conn = op.get_bind()

    def safe(sql: str):
        conn.execute(sa.text("SAVEPOINT sp"))
        try:
            conn.execute(sa.text(sql))
            conn.execute(sa.text("RELEASE SAVEPOINT sp"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp"))

    safe("ALTER TABLE articles ALTER COLUMN featured DROP DEFAULT")
    safe("ALTER TABLE articles ALTER COLUMN featured TYPE INTEGER USING featured::integer")
    safe("ALTER TABLE articles ALTER COLUMN featured SET DEFAULT 0")
