"""add_workflow_monitoring_fields

Revision ID: 245d2dd9956a
Revises: 020
Create Date: 2026-06-12 11:18:26.204664

"""
from typing import Sequence, Union
import sqlalchemy as sa
from app.core.alembic_helpers import (
    add_column_if_missing,
    create_index_if_missing,
    drop_column_if_exists,
    drop_index_if_exists,
)


revision: str = '245d2dd9956a'
down_revision: Union[str, None] = '020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Workflow tracking
    add_column_if_missing('articles', sa.Column('workflow_run_id', sa.String(length=255), nullable=True))
    add_column_if_missing('articles', sa.Column('completed_agent_keys', sa.Text(), nullable=True))
    add_column_if_missing('articles', sa.Column('next_agent_key', sa.String(length=100), nullable=True))
    add_column_if_missing('articles', sa.Column('agent_outputs_json', sa.JSON(), nullable=True))
    add_column_if_missing('articles', sa.Column('planning_brief_json', sa.JSON(), nullable=True))
    add_column_if_missing('articles', sa.Column('production_brief_json', sa.JSON(), nullable=True))
    add_column_if_missing('articles', sa.Column('workflow_status', sa.String(length=50), nullable=True))
    create_index_if_missing('ix_articles_workflow_run_id', 'articles', ['workflow_run_id'])

    # Target dates
    add_column_if_missing('articles', sa.Column('target_write_at', sa.DateTime(timezone=True), nullable=True))
    add_column_if_missing('articles', sa.Column('target_review_at', sa.DateTime(timezone=True), nullable=True))

    # Pre-brief fields
    add_column_if_missing('articles', sa.Column('main_answer_summary', sa.Text(), nullable=True))
    add_column_if_missing('articles', sa.Column('opportunity_justification', sa.Text(), nullable=True))
    add_column_if_missing('articles', sa.Column('recommended_format', sa.String(length=100), nullable=True))
    add_column_if_missing('articles', sa.Column('target_word_count', sa.Integer(), nullable=True))
    add_column_if_missing('articles', sa.Column('needs_faq', sa.Integer(), nullable=True))
    add_column_if_missing('articles', sa.Column('needs_images', sa.Integer(), nullable=True))
    add_column_if_missing('articles', sa.Column('suggested_internal_links', sa.Text(), nullable=True))
    add_column_if_missing('articles', sa.Column('suggested_external_links', sa.Text(), nullable=True))
    add_column_if_missing('articles', sa.Column('estimated_difficulty', sa.String(length=50), nullable=True))
    add_column_if_missing('articles', sa.Column('proposal_source', sa.String(length=255), nullable=True))

    # Monitoring / improvement
    add_column_if_missing('articles', sa.Column('improvement_proposal_json', sa.JSON(), nullable=True))
    add_column_if_missing('articles', sa.Column('performance_diagnosis_json', sa.JSON(), nullable=True))
    add_column_if_missing('articles', sa.Column('original_article_id', sa.String(), nullable=True))
    add_column_if_missing('articles', sa.Column('revision_of_article_id', sa.String(), nullable=True))
    add_column_if_missing('articles', sa.Column('proposed_changes_json', sa.JSON(), nullable=True))
    add_column_if_missing('articles', sa.Column('improvement_reason', sa.Text(), nullable=True))
    add_column_if_missing('articles', sa.Column('monitoring_status', sa.String(length=50), nullable=True))
    add_column_if_missing('articles', sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    drop_index_if_exists('ix_articles_workflow_run_id', 'articles')

    cols = [
        'next_review_at', 'monitoring_status', 'improvement_reason',
        'proposed_changes_json', 'revision_of_article_id', 'original_article_id',
        'performance_diagnosis_json', 'improvement_proposal_json',
        'proposal_source', 'estimated_difficulty', 'suggested_external_links',
        'suggested_internal_links', 'needs_images', 'needs_faq',
        'target_word_count', 'recommended_format', 'opportunity_justification',
        'main_answer_summary', 'target_review_at', 'target_write_at',
        'workflow_status', 'production_brief_json', 'planning_brief_json',
        'agent_outputs_json', 'next_agent_key', 'completed_agent_keys',
        'workflow_run_id',
    ]
    for c in cols:
        drop_column_if_exists('articles', c)
