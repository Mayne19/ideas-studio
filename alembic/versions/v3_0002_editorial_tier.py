"""add_article_editorial_tier

Ajoute content.articles.editorial_tier (pillar|cluster) : hiérarchie
éditoriale distincte de article_tier_service.py (qui calcule un tier de
volumétrie non persisté, stocké en artifact volume_tiers). Utilisé pour
forcer le maillage interne des articles cluster vers le pillar de leur
catégorie.

Revision ID: v3_0002
Revises: v3_0001
Create Date: 2026-08-05

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v3_0002"
down_revision: Union[str, None] = "v3_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("articles", schema="content")}
    if "editorial_tier" not in existing:
        op.add_column(
            "articles",
            sa.Column("editorial_tier", sa.Text(), nullable=True),
            schema="content",
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    existing = {c["name"] for c in insp.get_columns("articles", schema="content")}
    if "editorial_tier" in existing:
        with op.batch_alter_table("articles", schema="content") as batch:
            batch.drop_column("editorial_tier")
