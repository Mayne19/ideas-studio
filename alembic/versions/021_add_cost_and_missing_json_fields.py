"""Add cost fields to ai_usage_logs and missing JSON fields to articles

Revision ID: 021
Revises: 245d2dd9956a
Create Date: 2026-06-20 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '021'
down_revision: Union[str, None] = '245d2dd9956a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ai_usage_logs: add cost fields ──────────────────────────────────────
    with op.batch_alter_table('ai_usage_logs') as batch_op:
        batch_op.add_column(sa.Column('estimated_cost', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('actual_cost', sa.Float(), nullable=True))

    # ── articles: add missing JSON fields from PROJECT.MD ───────────────────
    with op.batch_alter_table('articles') as batch_op:
        # Phase 2 — Research (Sections 11.2-11.7)
        batch_op.add_column(sa.Column('serp_analysis_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('extracted_sources_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('content_gap_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('source_quality_report_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('evidence_pack_json', sa.JSON(), nullable=True))
        # Phase 3 — Strategy (Section 12.5)
        batch_op.add_column(sa.Column('cannibalization_outline_json', sa.JSON(), nullable=True))
        # Phase 5 — Writing (Sections 16.1, 16.5)
        batch_op.add_column(sa.Column('style_guide_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('structured_data_json', sa.JSON(), nullable=True))
        # Phase 6 — SEO/GEO (Section 17.2)
        batch_op.add_column(sa.Column('geo_optimization_json', sa.JSON(), nullable=True))
        # Phase 7 — Quality (Sections 18.4, 18.5)
        batch_op.add_column(sa.Column('claims_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('fact_check_report_json', sa.JSON(), nullable=True))
        # Cost estimation (Section 15)
        batch_op.add_column(sa.Column('estimated_cost_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('articles') as batch_op:
        cols = [
            'estimated_cost_json',
            'fact_check_report_json',
            'claims_json',
            'geo_optimization_json',
            'structured_data_json',
            'style_guide_json',
            'cannibalization_outline_json',
            'evidence_pack_json',
            'source_quality_report_json',
            'content_gap_json',
            'extracted_sources_json',
            'serp_analysis_json',
        ]
        for c in cols:
            batch_op.drop_column(c)

    with op.batch_alter_table('ai_usage_logs') as batch_op:
        batch_op.drop_column('actual_cost')
        batch_op.drop_column('estimated_cost')
