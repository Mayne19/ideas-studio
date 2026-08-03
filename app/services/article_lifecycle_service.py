"""États de publication d'un article — remplace les fonctions correspondantes
de app/services/article_service.py (encore sur l'ancien modèle plat, migré en
même temps que les routers/schémas Pydantic — voir REPRENDRE-LA-MAIN.md §6
étape 7). Scope volontairement limité à la machine à états explicitement visée
par l'étape 5 : publish pose published_revision_id, schedule ne le fait pas.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Article, ArticleRevision, ArticleScore
from app.models.reference import ArticleStatus, RevisionSource, set_article_status
from app.services.scoring_service import compute_global_score
from app.services.validation_service import check_validation_thresholds


def _next_revision_no(db: Session, article_id: str) -> int:
    last = db.execute(
        select(ArticleRevision.revision_no)
        .where(ArticleRevision.article_id == article_id)
        .order_by(ArticleRevision.revision_no.desc())
        .limit(1)
    ).scalar_one_or_none()
    return (last or 0) + 1


def _snapshot_revision(db: Session, article: Article, source: RevisionSource) -> ArticleRevision:
    """Copie la révision courante dans une nouvelle ligne — jamais de mutation
    en place d'une révision existante (content.article_revisions est un
    historique, voir db/migration-v3/01-schema.sql)."""
    current = article.current_revision
    if current is None:
        raise HTTPException(status_code=400, detail="Aucune révision courante à publier.")
    snapshot = ArticleRevision(
        article_id=article.id,
        revision_no=_next_revision_no(db, article.id),
        source=source,
        title=current.title,
        excerpt=current.excerpt,
        body=current.body,
        blocks=current.blocks,
        faq=current.faq,
        callouts=current.callouts,
        word_count=current.word_count,
        reading_time_minutes=current.reading_time_minutes,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _store_global_score(db: Session, article: Article) -> dict:
    scoring = compute_global_score(db, article.id, article=article)
    db.add(ArticleScore(
        article_id=article.id,
        revision_id=article.current_revision_id,
        global_score=scoring["global_score"],
        seo_score=scoring["seo_contrib"],
        eeat_score=scoring["eeat_contrib"],
        readability_score=scoring["readability_contrib"],
        geo_score=scoring["geo_contrib"],
    ))
    return scoring


def publish_article(db: Session, article: Article) -> Article:
    snapshot = _snapshot_revision(db, article, RevisionSource.HUMAN)
    article.published_revision_id = snapshot.id
    set_article_status(article, ArticleStatus.PUBLISHED)
    now = datetime.now(timezone.utc)
    if article.published_at is None:
        article.published_at = now
    article.updated_at = now
    _store_global_score(db, article)
    db.commit()
    db.refresh(article)
    return article


def schedule_article_with_validation(db: Session, article: Article, scheduled_at: datetime) -> Article:
    result = check_validation_thresholds(db, article, planned_publish_at=scheduled_at)
    if not result["valid"]:
        reasons = "; ".join(result["reasons"])
        raise HTTPException(
            status_code=400,
            detail=f"Article non validable pour la programmation : {reasons}",
        )

    _store_global_score(db, article)
    # "scheduled" NE requiert PAS published_revision_id — voir le commentaire sur
    # ref.article_status_reasons dans db/migration-v3/01-schema.sql : la
    # programmation n'est pas un instantané de publication, contrairement à publish.
    set_article_status(article, ArticleStatus.SCHEDULED)
    article.scheduled_for = scheduled_at
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


def unpublish_article(db: Session, article: Article) -> Article:
    # "unpublished" (130), pas "draft" : requires_revision=true, published_revision_id
    # reste posé (l'article a déjà été publié — voir ref.article_status_reasons).
    set_article_status(article, ArticleStatus.UNPUBLISHED)
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    try:
        from app.models.core import Project
        from app.services.publication_revalidation_service import trigger_project_revalidation

        project = db.get(Project, article.project_id)
        if project:
            trigger_project_revalidation(db, project, article=article, event_type="article.unpublished")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Revalidation after unpublish failed: %s", exc)
    return article


def unschedule_article(db: Session, article: Article) -> Article:
    set_article_status(article, ArticleStatus.DRAFT_READY)
    article.scheduled_for = None
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article


def rollback_article(db: Session, article: Article) -> Article:
    """Republie la dernière révision publiée (article.published_revision).
    Remplace l'ancien mécanisme ArticleVersion(version_type='publish_snapshot') :
    la révision publiée elle-même sert désormais de point de restauration."""
    published = article.published_revision
    if published is None:
        raise HTTPException(status_code=404, detail="Aucune révision publiée disponible pour le rollback.")

    restored = ArticleRevision(
        article_id=article.id,
        revision_no=_next_revision_no(db, article.id),
        source=RevisionSource.ROLLBACK,
        title=published.title,
        excerpt=published.excerpt,
        body=published.body,
        blocks=published.blocks,
        faq=published.faq,
        callouts=published.callouts,
        word_count=published.word_count,
        reading_time_minutes=published.reading_time_minutes,
    )
    db.add(restored)
    db.flush()
    article.current_revision_id = restored.id
    article.published_revision_id = restored.id
    set_article_status(article, ArticleStatus.PUBLISHED)
    article.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(article)
    return article
