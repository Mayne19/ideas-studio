"""add_pipeline_ideas_per_run_and_min_publish_score

Ajoute deux réglages projet sur ai.pipelines, éditables depuis l'interface
(Paramètres → Pipeline) :

- ideas_per_run (1-3, défaut 2) : plafond dur du nombre d'idées créées par
  lancement (pipeline, auto-génération, découverte, scheduler, planification
  mensuelle) — économise les crédits LLM ;
- min_publish_score (85-100, défaut 90) : score global de qualité minimum
  sous lequel la publication est bloquée (les sous-scores heuristiques
  restent de simples avertissements).

Migration purement additive : deux colonnes NOT NULL avec valeur par défaut
serveur (PostgreSQL 11+ : pas de réécriture de table) et deux contraintes
CHECK. Aucune donnée existante n'est modifiée.

Revision ID: v3_0006
Revises: v3_0005
Create Date: 2026-10-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v3_0006"
down_revision: Union[str, None] = "v3_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "pipelines"
SCHEMA = "ai"


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns(TABLE, schema=SCHEMA)}
    if "ideas_per_run" not in existing:
        op.add_column(
            TABLE,
            sa.Column("ideas_per_run", sa.SmallInteger(), nullable=False, server_default=sa.text("2")),
            schema=SCHEMA,
        )
    if "min_publish_score" not in existing:
        op.add_column(
            TABLE,
            sa.Column("min_publish_score", sa.SmallInteger(), nullable=False, server_default=sa.text("90")),
            schema=SCHEMA,
        )

    checks = {c["name"] for c in insp.get_check_constraints(TABLE, schema=SCHEMA)}
    if "pipelines_ideas_per_run_range" not in checks:
        op.create_check_constraint(
            "pipelines_ideas_per_run_range", TABLE,
            "ideas_per_run BETWEEN 1 AND 3", schema=SCHEMA,
        )
    if "pipelines_min_publish_score_range" not in checks:
        op.create_check_constraint(
            "pipelines_min_publish_score_range", TABLE,
            "min_publish_score BETWEEN 85 AND 100", schema=SCHEMA,
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    checks = {c["name"] for c in insp.get_check_constraints(TABLE, schema=SCHEMA)}
    for name in ("pipelines_min_publish_score_range", "pipelines_ideas_per_run_range"):
        if name in checks:
            op.drop_constraint(name, TABLE, schema=SCHEMA, type_="check")
    existing = {c["name"] for c in insp.get_columns(TABLE, schema=SCHEMA)}
    for column in ("min_publish_score", "ideas_per_run"):
        if column in existing:
            op.drop_column(TABLE, column, schema=SCHEMA)
