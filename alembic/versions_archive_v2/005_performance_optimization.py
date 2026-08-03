"""005 performance optimization notifications

Revision ID: 005
Revises: 004
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "optimization_recommendations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("article_id", sa.String(), sa.ForeignKey("articles.id"), nullable=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_optimization_recommendations_project_id", "optimization_recommendations", ["project_id"])
    op.create_index("ix_optimization_recommendations_article_id", "optimization_recommendations", ["article_id"])
    op.create_index("ix_optimization_recommendations_status", "optimization_recommendations", ["status"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("type", sa.String(100), nullable=False, server_default="system"),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("level", sa.String(20), nullable=False, server_default="info"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_project_id", "notifications", ["project_id"])
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    # search_console_metrics_json placeholder on articles
    op.add_column("articles", sa.Column("search_console_metrics_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "search_console_metrics_json")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_project_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_optimization_recommendations_status", table_name="optimization_recommendations")
    op.drop_index("ix_optimization_recommendations_article_id", table_name="optimization_recommendations")
    op.drop_index("ix_optimization_recommendations_project_id", table_name="optimization_recommendations")
    op.drop_table("optimization_recommendations")
