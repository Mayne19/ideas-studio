"""readability_report_json_global_score_index_featured_boolean

Revision ID: 4d6055864a7a
Revises: aa3b49450126
Create Date: 2026-06-29 09:50:46.653020

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '4d6055864a7a'
down_revision: Union[str, None] = 'aa3b49450126'
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

    safe("ALTER TABLE articles ADD COLUMN IF NOT EXISTS readability_report_json JSON")
    safe("CREATE INDEX IF NOT EXISTS ix_articles_global_score ON articles (global_score)")
    safe("ALTER TABLE articles ALTER COLUMN featured TYPE BOOLEAN USING featured::boolean")


def downgrade() -> None:
    conn = op.get_bind()

    def safe(sql: str):
        conn.execute(sa.text("SAVEPOINT sp"))
        try:
            conn.execute(sa.text(sql))
            conn.execute(sa.text("RELEASE SAVEPOINT sp"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp"))

    safe("ALTER TABLE articles ALTER COLUMN featured TYPE INTEGER USING featured::integer")
    safe("DROP INDEX IF EXISTS ix_articles_global_score")
    safe("ALTER TABLE articles DROP COLUMN IF EXISTS readability_report_json")
