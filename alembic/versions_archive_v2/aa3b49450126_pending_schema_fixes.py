"""pending_schema_fixes

Revision ID: aa3b49450126
Revises: 5ac6925c87bc
Create Date: 2026-06-29 07:18:44.046416

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'aa3b49450126'
down_revision: Union[str, None] = '5ac6925c87bc'
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

    safe("ALTER TABLE agent_assignments ADD CONSTRAINT uq_project_agent_assignment UNIQUE (project_id, agent_id)")
    safe("ALTER TABLE ai_provider_configs ADD CONSTRAINT uq_project_provider UNIQUE (project_id, provider)")
    safe("ALTER TABLE articles ADD CONSTRAINT fk_articles_original_article_id FOREIGN KEY (original_article_id) REFERENCES articles(id) NOT VALID")
    safe("ALTER TABLE articles ADD CONSTRAINT fk_articles_revision_of_article_id FOREIGN KEY (revision_of_article_id) REFERENCES articles(id) NOT VALID")
    safe("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS link VARCHAR(500)")
    safe("ALTER TABLE users ADD CONSTRAINT uq_users_username UNIQUE (username)")


def downgrade() -> None:
    conn = op.get_bind()

    def safe(sql: str):
        conn.execute(sa.text("SAVEPOINT sp"))
        try:
            conn.execute(sa.text(sql))
            conn.execute(sa.text("RELEASE SAVEPOINT sp"))
        except Exception:
            conn.execute(sa.text("ROLLBACK TO SAVEPOINT sp"))

    safe("ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_username")
    safe("ALTER TABLE notifications DROP COLUMN IF EXISTS link")
    safe("ALTER TABLE articles DROP CONSTRAINT IF EXISTS fk_articles_revision_of_article_id")
    safe("ALTER TABLE articles DROP CONSTRAINT IF EXISTS fk_articles_original_article_id")
    safe("ALTER TABLE ai_provider_configs DROP CONSTRAINT IF EXISTS uq_project_provider")
    safe("ALTER TABLE agent_assignments DROP CONSTRAINT IF EXISTS uq_project_agent_assignment")
