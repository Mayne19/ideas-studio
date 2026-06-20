"""add pipeline settings and logs tables

Revision ID: 012
Revises: 011
Create Date: 2026-05-17 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def upgrade():
    if not _table_exists("project_pipelines"):
        op.create_table(
            "project_pipelines",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("active_days", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("launch_hour", sa.Integer(), nullable=False, server_default="8"),
            sa.Column("articles_per_week", sa.Integer(), nullable=False, server_default="5"),
            sa.Column("category_priorities", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("project_id", name="uq_project_pipelines_project_id"),
        )
    else:
        _add_column_if_missing("project_pipelines", sa.Column("id", sa.String(), nullable=True))
        _add_column_if_missing("project_pipelines", sa.Column("project_id", sa.String(), nullable=True))
        _add_column_if_missing("project_pipelines", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        _add_column_if_missing("project_pipelines", sa.Column("active_days", sa.Text(), nullable=False, server_default="[]"))
        _add_column_if_missing("project_pipelines", sa.Column("launch_hour", sa.Integer(), nullable=False, server_default="8"))
        _add_column_if_missing("project_pipelines", sa.Column("articles_per_week", sa.Integer(), nullable=False, server_default="5"))
        _add_column_if_missing("project_pipelines", sa.Column("category_priorities", sa.Text(), nullable=False, server_default="{}"))
        _add_column_if_missing("project_pipelines", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        _add_column_if_missing("project_pipelines", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    if not _index_exists("project_pipelines", "ix_project_pipelines_project_id"):
        op.create_index("ix_project_pipelines_project_id", "project_pipelines", ["project_id"])

    if not _table_exists("pipeline_logs"):
        op.create_table(
            "pipeline_logs",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("project_id", sa.String(), nullable=False),
            sa.Column("status", sa.String(50), nullable=False),
            sa.Column("ideas_generated", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("articles_created", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("errors", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        _add_column_if_missing("pipeline_logs", sa.Column("id", sa.String(), nullable=True))
        _add_column_if_missing("pipeline_logs", sa.Column("project_id", sa.String(), nullable=True))
        _add_column_if_missing("pipeline_logs", sa.Column("status", sa.String(50), nullable=False, server_default="completed"))
        _add_column_if_missing("pipeline_logs", sa.Column("ideas_generated", sa.Integer(), nullable=False, server_default="0"))
        _add_column_if_missing("pipeline_logs", sa.Column("articles_created", sa.Integer(), nullable=False, server_default="0"))
        _add_column_if_missing("pipeline_logs", sa.Column("errors", sa.Text(), nullable=True))
        _add_column_if_missing("pipeline_logs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
        _add_column_if_missing("pipeline_logs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))

    if not _index_exists("pipeline_logs", "ix_pipeline_logs_project_id"):
        op.create_index("ix_pipeline_logs_project_id", "pipeline_logs", ["project_id"])


def downgrade():
    if _table_exists("pipeline_logs"):
        op.drop_table("pipeline_logs")
    if _table_exists("project_pipelines"):
        op.drop_table("project_pipelines")
