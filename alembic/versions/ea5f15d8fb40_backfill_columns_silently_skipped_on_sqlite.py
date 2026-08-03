"""backfill_columns_silently_skipped_on_sqlite

Revision ID: ea5f15d8fb40
Revises: a5c7e9b1d3f5
Create Date: 2026-08-03

Plusieurs anciennes migrations ajoutaient des colonnes via
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` enveloppé dans un
SAVEPOINT/ROLLBACK "safe()". Cette syntaxe n'existe pas sur SQLite
(`OperationalError: near "EXISTS": syntax error`) : l'erreur était
avalée silencieusement par le wrapper, si bien que ces colonnes n'ont
jamais été créées sur SQLite (dev), alors qu'elles le sont bien sur
PostgreSQL (prod) où `IF NOT EXISTS` est supporté. Résultat concret :
`db.query(Project)` (utilisé par listCategories, listCalloutTemplates,
listMembers, plusieurs routes articles...) levait
"no such column: projects.vertical" et faisait échouer le chargement
de l'éditeur d'article en dev.

Cette migration comble ces colonnes partout où elles manquent encore,
via l'inspecteur SQLAlchemy (idempotent, sans effet sur les bases où
la colonne existe déjà) :
  - projects.vertical
  - notifications.link
  - articles.readability_report_json
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'ea5f15d8fb40'
down_revision: Union[str, None] = 'a5c7e9b1d3f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES_COLUMNS = {
    "projects": [("vertical", sa.String(length=100))],
    "notifications": [("link", sa.String(length=1000))],
    "articles": [("readability_report_json", sa.JSON())],
}


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    for table, columns in TABLES_COLUMNS.items():
        existing = {c["name"] for c in insp.get_columns(table)}
        for name, col_type in columns:
            if name not in existing:
                op.add_column(table, sa.Column(name, col_type, nullable=True))

    existing_project_indexes = {ix["name"] for ix in insp.get_indexes("projects")}
    if "ix_projects_vertical" not in existing_project_indexes:
        op.create_index("ix_projects_vertical", "projects", ["vertical"])


def downgrade() -> None:
    # Colonnes potentiellement utiles ailleurs (créées correctement sur les
    # bases où la migration d'origine avait fonctionné) : pas de downgrade
    # destructif, cette migration ne fait que compléter un état incomplet.
    pass
