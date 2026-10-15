"""add_generation_jobs

Ajoute ai.generation_jobs : suivi des générations d'article lancées depuis
l'interface et exécutées en tâche de fond (POST /articles/generate répond
202 avec l'id du job ; le proxy Railway coupait la requête synchrone à 300 s
alors qu'un article prend 7 à 12 min). Statut porté par
ref.run_status_reasons (queued/running/succeeded/failed), comme
ai.workflow_runs.

Migration purement additive (nouvelle table + index) : aucune donnée
existante n'est touchée, aucune table existante n'est verrouillée au-delà de
la création des clés étrangères.

Revision ID: v3_0005
Revises: v3_0004
Create Date: 2026-10-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v3_0005"
down_revision: Union[str, None] = "v3_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "generation_jobs"


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(TABLE, schema="ai"):
        op.create_table(
            TABLE,
            sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column(
                "project_id", postgresql.UUID(as_uuid=False),
                sa.ForeignKey("core.projects.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column(
                "user_id", postgresql.UUID(as_uuid=False),
                sa.ForeignKey("core.users.id", ondelete="SET NULL"), nullable=True,
            ),
            sa.Column(
                "article_id", postgresql.UUID(as_uuid=False),
                sa.ForeignKey("content.articles.id", ondelete="SET NULL"), nullable=True,
            ),
            sa.Column("state_id", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
            sa.Column("status_reason_id", sa.SmallInteger(), nullable=False, server_default=sa.text("10")),
            sa.Column("request", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("current_step", sa.Text(), nullable=True),
            sa.Column("steps_completed", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(
                ["status_reason_id", "state_id"],
                ["ref.run_status_reasons.id", "ref.run_status_reasons.state_id"],
            ),
            schema="ai",
        )

    # Nouvel inspecteur : celui du dessus a pu mettre en cache l'absence de
    # la table avant sa création.
    insp = sa.inspect(op.get_bind())
    existing_indexes = {ix["name"] for ix in insp.get_indexes(TABLE, schema="ai")}
    if "generation_jobs_project_idx" not in existing_indexes:
        op.create_index(
            "generation_jobs_project_idx",
            TABLE,
            ["project_id", sa.text("created_at DESC")],
            schema="ai",
        )
    if "generation_jobs_active_idx" not in existing_indexes:
        # Reprise au démarrage : seuls les jobs queued/running sont relus.
        op.create_index(
            "generation_jobs_active_idx",
            TABLE,
            ["status_reason_id"],
            schema="ai",
            postgresql_where=sa.text("status_reason_id IN (10, 20)"),
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if insp.has_table(TABLE, schema="ai"):
        op.drop_table(TABLE, schema="ai")
