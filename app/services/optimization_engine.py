from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analytics import OptimizationRecommendation, TrafficEvent
from app.models.content import Article, ArticleScore
from app.models.reference import ArticleStatus, RunStatus, set_run_status
from app.services.notification_service import create_notification

_LOW_TRAFFIC_THRESHOLD = 5
_LOW_SEO_THRESHOLD = 50.0
_DAYS_J7 = 7
_DAYS_J30 = 30
_DAYS_J90 = 90

# analytics.optimization_recommendations réutilise ref.run_status_reasons
# (queued/running/succeeded/failed/cancelled) — voir 01-schema.sql. Mapping
# retenu : pending=QUEUED, accepted=RUNNING (en cours de traitement),
# applied=SUCCEEDED, rejected=CANCELLED. "failed" n'a pas d'équivalent ici.
_STATUS_CODE_TO_RUN_STATUS = {
    "pending": RunStatus.QUEUED,
    "accepted": RunStatus.RUNNING,
    "applied": RunStatus.SUCCEEDED,
    "rejected": RunStatus.CANCELLED,
}
_RUN_STATUS_TO_CODE = {v: k for k, v in _STATUS_CODE_TO_RUN_STATUS.items()}


def status_code(status_reason_id: int) -> str:
    return _RUN_STATUS_TO_CODE.get(status_reason_id, "pending")


def set_recommendation_status(rec: OptimizationRecommendation, code: str) -> None:
    set_run_status(rec, _STATUS_CODE_TO_RUN_STATUS[code])


def to_public(rec: OptimizationRecommendation) -> dict:
    return {
        "id": rec.id,
        "project_id": rec.project_id,
        "article_id": rec.article_id,
        "type": rec.type,
        "priority": rec.priority,
        "reason": rec.reason,
        "suggestion": rec.suggestion,
        "status": status_code(rec.status_reason_id),
        "created_at": rec.created_at,
        "resolved_at": rec.resolved_at,
    }


def _pending_exists(db: Session, project_id: str, article_id: str, rec_type: str) -> bool:
    return db.execute(
        select(OptimizationRecommendation).where(
            OptimizationRecommendation.project_id == project_id,
            OptimizationRecommendation.article_id == article_id,
            OptimizationRecommendation.type == rec_type,
            OptimizationRecommendation.status_reason_id == RunStatus.QUEUED,
        )
    ).scalar_one_or_none() is not None


def _add_rec(
    db: Session,
    project_id: str,
    article_id: str,
    rec_type: str,
    reason: str,
    suggestion: str,
    priority: int = 0,
) -> OptimizationRecommendation | None:
    if _pending_exists(db, project_id, article_id, rec_type):
        return None
    rec = OptimizationRecommendation(
        project_id=project_id,
        article_id=article_id,
        type=rec_type,
        reason=reason,
        suggestion=suggestion,
        priority=priority,
    )
    set_recommendation_status(rec, "pending")
    db.add(rec)
    db.flush()
    return rec


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _classify_phase(published_at: datetime) -> str:
    age = (datetime.now(timezone.utc) - _as_utc(published_at)).days
    if age >= _DAYS_J90:
        return "j90"
    if age >= _DAYS_J30:
        return "j30"
    if age >= _DAYS_J7:
        return "j7"
    return "too_recent"


def review_published_articles(db: Session, project_id: str) -> dict:
    articles = db.execute(
        select(Article).where(
            Article.project_id == project_id,
            Article.status_reason_id == ArticleStatus.PUBLISHED,
            Article.published_at.isnot(None),
        )
    ).scalars().all()

    created_count = 0
    skipped_count = 0
    notifications_created = 0

    for article in articles:
        phase = _classify_phase(article.published_at)
        if phase == "too_recent":
            continue

        recs_before = created_count
        revision = article.current_revision
        title = revision.title if revision else ""
        faq = revision.faq if revision else []

        from app.models.content import ArticleSeo
        seo = db.get(ArticleSeo, article.id)
        meta_description = seo.meta_description if seo else None

        latest_score = db.execute(
            select(ArticleScore)
            .where(ArticleScore.article_id == article.id)
            .order_by(ArticleScore.evaluated_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        # fix_low_traffic: J+30 or J+90, zero or very low traffic views
        if phase in ("j30", "j90"):
            views = _get_article_view_count(db, article)
            if views < _LOW_TRAFFIC_THRESHOLD:
                r = _add_rec(
                    db, project_id, article.id,
                    "fix_low_traffic",
                    f"Article publié il y a {(datetime.now(timezone.utc) - _as_utc(article.published_at)).days} jours avec seulement {views} vue(s).",
                    "Améliorez le titre, la meta description ou renforcez le maillage interne pour augmenter le trafic.",
                    priority=2,
                )
                if r:
                    created_count += 1

        # add_faq
        if not faq:
            r = _add_rec(
                db, project_id, article.id,
                "add_faq",
                "L'article n'a pas de section FAQ.",
                "Ajoutez une section FAQ avec 3-5 questions fréquentes liées au mot-clé principal.",
                priority=1,
            )
            if r:
                created_count += 1

        # improve_meta_description
        meta_desc = meta_description or ""
        if not meta_desc or len(meta_desc) < 120:
            r = _add_rec(
                db, project_id, article.id,
                "improve_meta_description",
                f"La meta description est trop courte ({len(meta_desc)} caractères).",
                "Rédigez une meta description entre 120 et 160 caractères intégrant le mot-clé.",
                priority=1,
            )
            if r:
                created_count += 1

        # improve SEO score
        seo_score = float(latest_score.seo_score) if latest_score and latest_score.seo_score is not None else None
        if seo_score is not None and seo_score < _LOW_SEO_THRESHOLD:
            r = _add_rec(
                db, project_id, article.id,
                "improve_title",
                f"Le score SEO est faible ({seo_score:.0f}/100).",
                "Optimisez le titre, le H1 et intégrez mieux le mot-clé principal.",
                priority=2,
            )
            if r:
                created_count += 1

        # add_internal_links
        from app.models.content import ArticleLink
        has_internal_links = db.execute(
            select(ArticleLink.id).where(ArticleLink.article_id == article.id, ArticleLink.kind == "internal").limit(1)
        ).scalar_one_or_none() is not None
        if not has_internal_links:
            r = _add_rec(
                db, project_id, article.id,
                "add_internal_links",
                "L'article n'a pas de liens internes enregistrés.",
                "Ajoutez 2-3 liens vers d'autres articles du même projet pour renforcer le maillage interne.",
                priority=0,
            )
            if r:
                created_count += 1

        new_recs = created_count - recs_before
        if new_recs > 0:
            create_notification(
                db,
                project_id=project_id,
                title=f"Nouvelles recommandations pour « {title[:60]} »",
                message=f"{new_recs} recommandation(s) d'optimisation créée(s) pour cet article.",
                level="info",
                type="optimization",
                link=f"/projects/{project_id}/articles/{article.id}/edit",
            )
            notifications_created += 1
        else:
            skipped_count += 1

    db.flush()
    return {
        "articles_reviewed": len(articles),
        "recommendations_created": created_count,
        "articles_skipped": skipped_count,
        "notifications_created": notifications_created,
    }


def _get_article_view_count(db: Session, article: Article) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=_DAYS_J90)
    slug = article.slug or ""
    if not slug:
        return 0

    events = db.execute(
        select(TrafficEvent).where(
            TrafficEvent.project_id == article.project_id,
            TrafficEvent.occurred_at >= since,
        )
    ).scalars().all()
    return sum(1 for e in events if slug in e.path)
