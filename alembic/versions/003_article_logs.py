"""article logs

Revision ID: 003
Revises: 002
Create Date: 2026-05-05
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "article_logs",
        sa.Column("id", sa.String(), primary_key=True, nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("article_id", sa.String(), sa.ForeignKey("articles.id"), nullable=True),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("step", sa.String(100), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_article_logs_project_id", "article_logs", ["project_id"])
    op.create_index("ix_article_logs_article_id", "article_logs", ["article_id"])


def downgrade() -> None:
    op.drop_index("ix_article_logs_article_id", table_name="article_logs")
    op.drop_index("ix_article_logs_project_id", table_name="article_logs")
    op.drop_table("article_logs")
