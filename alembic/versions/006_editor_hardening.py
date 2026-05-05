"""006 editor hardening: article_versions, media_assets, content_blocks_json

Revision ID: 006
Revises: 005
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_versions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("article_id", sa.String(), sa.ForeignKey("articles.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("meta_title", sa.String(255), nullable=True),
        sa.Column("meta_description", sa.String(500), nullable=True),
        sa.Column("cover_image_url", sa.String(1000), nullable=True),
        sa.Column("faq_json", sa.Text(), nullable=True),
        sa.Column("callouts_json", sa.Text(), nullable=True),
        sa.Column("internal_links_json", sa.Text(), nullable=True),
        sa.Column("external_links_json", sa.Text(), nullable=True),
        sa.Column("content_blocks_json", sa.Text(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("version_type", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_article_versions_article_id", "article_versions", ["article_id"])
    op.create_index("ix_article_versions_project_id", "article_versions", ["project_id"])

    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("article_id", sa.String(), sa.ForeignKey("articles.id"), nullable=True),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("alt_text", sa.String(500), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("source", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_media_assets_project_id", "media_assets", ["project_id"])
    op.create_index("ix_media_assets_article_id", "media_assets", ["article_id"])

    op.add_column("articles", sa.Column("content_blocks_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("articles", "content_blocks_json")
    op.drop_index("ix_media_assets_article_id", table_name="media_assets")
    op.drop_index("ix_media_assets_project_id", table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_index("ix_article_versions_project_id", table_name="article_versions")
    op.drop_index("ix_article_versions_article_id", table_name="article_versions")
    op.drop_table("article_versions")
