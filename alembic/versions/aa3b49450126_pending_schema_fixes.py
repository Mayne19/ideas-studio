"""pending_schema_fixes

Revision ID: aa3b49450126
Revises: 5ac6925c87bc
Create Date: 2026-06-29 07:18:44.046416

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = 'aa3b49450126'
down_revision: Union[str, None] = '5ac6925c87bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _try_create_unique_constraint(constraint_name, table, columns):
    """Add a unique constraint, silently skip if it already exists or data violates it."""
    try:
        op.create_unique_constraint(constraint_name, table, columns)
    except Exception:
        pass


def upgrade() -> None:
    _try_create_unique_constraint('uq_project_agent_assignment', 'agent_assignments', ['project_id', 'agent_id'])
    _try_create_unique_constraint('uq_project_provider', 'ai_provider_configs', ['project_id', 'provider'])

    # FK auto-référentes : use_alter=True évite les deadlocks sur tables peuplées
    try:
        op.create_foreign_key(
            'fk_articles_original_article_id', 'articles', 'articles',
            ['original_article_id'], ['id'],
            use_alter=True,
        )
    except Exception:
        pass

    try:
        op.create_foreign_key(
            'fk_articles_revision_of_article_id', 'articles', 'articles',
            ['revision_of_article_id'], ['id'],
            use_alter=True,
        )
    except Exception:
        pass

    op.add_column('notifications', sa.Column('link', sa.String(length=1000), nullable=True))

    # Contrainte UNIQUE sur users.username : vérifier doublons et NULL avant d'ajouter
    conn = op.get_bind()
    duplicate_count = conn.execute(
        text(
            "SELECT COUNT(*) FROM ("
            "  SELECT username FROM users"
            "  WHERE username IS NOT NULL"
            "  GROUP BY username HAVING COUNT(*) > 1"
            ") AS dups"
        )
    ).scalar()
    null_count = conn.execute(
        text("SELECT COUNT(*) FROM users WHERE username IS NULL")
    ).scalar()

    if duplicate_count == 0 and null_count == 0:
        _try_create_unique_constraint(None, 'users', ['username'])


def downgrade() -> None:
    try:
        op.drop_constraint(None, 'users', type_='unique')
    except Exception:
        pass
    op.drop_column('notifications', 'link')
    try:
        op.drop_constraint('fk_articles_revision_of_article_id', 'articles', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_constraint('fk_articles_original_article_id', 'articles', type_='foreignkey')
    except Exception:
        pass
    try:
        op.drop_constraint('uq_project_provider', 'ai_provider_configs', type_='unique')
    except Exception:
        pass
    try:
        op.drop_constraint('uq_project_agent_assignment', 'agent_assignments', type_='unique')
    except Exception:
        pass
