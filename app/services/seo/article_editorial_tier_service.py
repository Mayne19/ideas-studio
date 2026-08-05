from __future__ import annotations

"""Hiérarchie éditoriale pillar/cluster — distincte de article_tier_service.py
(qui calcule un tier de VOLUMÉTRIE non persisté, en artifact volume_tiers).

Ici : le premier article publié ou en file d'une catégorie devient son
pillar (page de référence recevant des liens de tous les autres articles
de la catégorie) ; les suivants sont des cluster (doivent lier leur pillar).
Persisté sur Article.editorial_tier ("pillar" | "cluster"), colonne ajoutée
par la migration v3_0002_editorial_tier.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Article
from app.models.reference import ArticleStatus

_COUNTED_STATUSES = (
    ArticleStatus.PUBLISHED,
    ArticleStatus.DRAFT,
    ArticleStatus.DRAFT_READY,
    ArticleStatus.WRITING_IN_PROGRESS,
)


def get_category_pillar(db: Session, project_id: str, category_id: str, exclude_article_id: str | None = None) -> Article | None:
    """Le pillar déjà assigné pour cette catégorie, s'il existe."""
    if not category_id:
        return None
    query = select(Article).where(
        Article.project_id == project_id,
        Article.category_id == category_id,
        Article.editorial_tier == "pillar",
    )
    if exclude_article_id:
        query = query.where(Article.id != exclude_article_id)
    return db.execute(query.order_by(Article.created_at.asc()).limit(1)).scalar_one_or_none()


def resolve_editorial_tier(db: Session, project_id: str, category_id: str | None, article_id: str | None = None) -> str:
    """Détermine le tier de l'article en cours de génération.

    pillar si c'est le premier article (publié ou en cours) de sa catégorie
    dans ce projet, cluster sinon. Un article sans catégorie est toujours
    cluster (pas de hiérarchie possible sans regroupement)."""
    if not category_id:
        return "cluster"

    existing_pillar = get_category_pillar(db, project_id, category_id, exclude_article_id=article_id)
    if existing_pillar is not None:
        return "cluster"

    other_count = db.execute(
        select(Article.id).where(
            Article.project_id == project_id,
            Article.category_id == category_id,
            Article.status_reason_id.in_(_COUNTED_STATUSES),
            Article.id != article_id if article_id else True,
        ).limit(1)
    ).scalar_one_or_none()

    return "cluster" if other_count is not None else "pillar"
