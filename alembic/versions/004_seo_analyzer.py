"""004 seo analyzer

Revision ID: 004
Revises: 003
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_analyses",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("article_id", sa.String(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("seo_score", sa.Float(), nullable=False),
        sa.Column("readability_score", sa.Float(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("eeat_score", sa.Float(), nullable=False),
        sa.Column("readiness_status", sa.String(50), nullable=False),
        sa.Column("issues_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("suggestions_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_seo_analyses_project_id", "seo_analyses", ["project_id"])
    op.create_index("ix_seo_analyses_article_id", "seo_analyses", ["article_id"])

    # New columns on articles
    op.add_column("articles", sa.Column("faq_json", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("callouts_json", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("internal_links_json", sa.Text(), nullable=True))
    op.add_column("articles", sa.Column("external_links_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "external_links_json")
    op.drop_column("articles", "internal_links_json")
    op.drop_column("articles", "callouts_json")
    op.drop_column("articles", "faq_json")
    op.drop_index("ix_seo_analyses_article_id", table_name="seo_analyses")
    op.drop_index("ix_seo_analyses_project_id", table_name="seo_analyses")
    op.drop_table("seo_analyses")
