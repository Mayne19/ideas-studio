"""add article_comments table

Revision ID: 015_add_article_comments
Revises: 014_seo_workflow_fields
Create Date: 2026-06-11 10:00:00.000000

"""
import sqlalchemy as sa
from app.core.alembic_helpers import (
    create_index_if_missing,
    create_table_if_missing,
    drop_index_if_exists,
    drop_table_if_exists,
)


revision = '015_add_article_comments'
down_revision = '014_seo_workflow_fields'
branch_labels = None
depends_on = None


def upgrade():
    create_table_if_missing(
        'article_comments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('article_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('author_id', sa.String(), nullable=False),
        sa.Column('author_name', sa.String(length=255), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('selected_text', sa.Text(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    create_index_if_missing('ix_article_comments_article_id', 'article_comments', ['article_id'])
    create_index_if_missing('ix_article_comments_project_id', 'article_comments', ['project_id'])


def downgrade():
    drop_index_if_exists('ix_article_comments_project_id', 'article_comments')
    drop_index_if_exists('ix_article_comments_article_id', 'article_comments')
    drop_table_if_exists('article_comments')
