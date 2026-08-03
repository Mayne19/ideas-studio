"""add_vertical_to_projects

Revision ID: eb654f66829e
Revises: 4d6055864a7a
Create Date: 2026-06-29 13:35:03.719883

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'eb654f66829e'
down_revision: Union[str, None] = '4d6055864a7a'
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

    safe("ALTER TABLE projects ADD COLUMN IF NOT EXISTS vertical VARCHAR(100)")
    safe("CREATE INDEX IF NOT EXISTS ix_projects_vertical ON projects (vertical)")


def downgrade() -> None:
    conn = op.get_bind()

    def safe(sql: str):
        conn.execute(sa.text("SAVEPOINT sp"))
        try:
            conn.execute(sa.text(sql))
            conn.execute(sa.text("RELEASE SAVEPOINT sp"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp"))

    safe("DROP INDEX IF EXISTS ix_projects_vertical")
    safe("ALTER TABLE projects DROP COLUMN IF EXISTS vertical")
