"""add article_comments table

Revision ID: 015_add_article_comments
Revises: 014_seo_workflow_fields
Create Date: 2026-06-11 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '015_add_article_comments'
down_revision = '014_seo_workflow_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'article_comments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('article_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('author_id', sa.String(), nullable=False),
        sa.Column('author_name', sa.String(length=255), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('selected_text', sa.Text(), nullable=True),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_article_comments_article_id'), 'article_comments', ['article_id'], unique=False)
    op.create_index(op.f('ix_article_comments_project_id'), 'article_comments', ['project_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_article_comments_project_id'), table_name='article_comments')
    op.drop_index(op.f('ix_article_comments_article_id'), table_name='article_comments')
    op.drop_table('article_comments')
