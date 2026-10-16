"""Image de couverture d'un article : content.article_media (role = cover)
pointant vers un content.media_assets. Pas de colonne cover_image_url en v3 :
l'URL est lue via cette jointure (API publique, aperçu, données structurées).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Article, ArticleMedia, MediaAsset
from app.models.reference import MediaRole


def get_cover_image_url(db: Session, article_id: str) -> str | None:
    return db.execute(
        select(MediaAsset.url)
        .join(ArticleMedia, ArticleMedia.media_id == MediaAsset.id)
        .where(ArticleMedia.article_id == article_id, ArticleMedia.role == MediaRole.COVER)
        .order_by(ArticleMedia.position.asc())
        .limit(1)
    ).scalar_one_or_none()


def set_cover_image_if_missing(db: Session, article: Article, source: dict | None) -> str | None:
    """Pose `source` (image sourcée par le plan d'images) comme couverture si
    l'article n'en a pas encore — une couverture choisie par l'éditeur n'est
    jamais remplacée. Retourne l'URL de la couverture effective."""
    existing = get_cover_image_url(db, article.id)
    if existing or not source or not source.get("image_url"):
        return existing

    from app.services.seo.image_plan_service import image_alt_text, is_unsplash_source

    url = source["image_url"]
    author = (source.get("author") or "").strip()
    caption = f"Photo : {author} sur Unsplash" if is_unsplash_source(source) and author else None
    asset = MediaAsset(
        project_id=article.project_id,
        url=url,
        filename=url.rsplit("/", 1)[-1].split("?", 1)[0][:200] or "cover",
        alt_text=image_alt_text(source) or None,
        caption=caption,
        source=(source.get("source_name") or "").lower() or None,
    )
    db.add(asset)
    db.flush()
    db.add(ArticleMedia(article_id=article.id, media_id=asset.id, role=MediaRole.COVER, position=0))
    db.flush()
    return url
