from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.article import Article
from app.models.optimization_recommendation import OptimizationRecommendation
from app.services.notification_service import create_notification


_LOW_TRAFFIC_THRESHOLD = 5
_LOW_SEO_THRESHOLD = 50.0
_DAYS_J7 = 7
_DAYS_J30 = 30
_DAYS_J90 = 90


def _pending_exists(db: Session, project_id: str, article_id: str, rec_type: str) -> bool:
    return (
        db.query(OptimizationRecommendation)
        .filter(
            OptimizationRecommendation.project_id == project_id,
            OptimizationRecommendation.article_id == article_id,
            OptimizationRecommendation.type == rec_type,
            OptimizationRecommendation.status == "pending",
        )
        .first()
        is not None
    )


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
    articles = (
        db.query(Article)
        .filter(
            Article.project_id == project_id,
            Article.status == "published",
            Article.published_at.isnot(None),
        )
        .all()
    )

    created_count = 0
    skipped_count = 0
    notifications_created = 0

    for article in articles:
        phase = _classify_phase(article.published_at)
        if phase == "too_recent":
            continue

        recs_before = created_count

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
        if not article.faq_json or article.faq_json == "[]":
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
        meta_desc = article.meta_description or ""
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
        if article.seo_score is not None and article.seo_score < _LOW_SEO_THRESHOLD:
            r = _add_rec(
                db, project_id, article.id,
                "improve_title",
                f"Le score SEO est faible ({article.seo_score:.0f}/100).",
                "Optimisez le titre, le H1 et intégrez mieux le mot-clé principal.",
                priority=2,
            )
            if r:
                created_count += 1

        # add_internal_links
        if not article.internal_links_json or article.internal_links_json == "[]":
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
                title=f"Nouvelles recommandations pour « {article.title[:60]} »",
                message=f"{new_recs} recommandation(s) d'optimisation créée(s) pour cet article.",
                level="info",
                type="optimization",
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
    from app.models.traffic_event import TrafficEvent
    from datetime import timedelta

    since = datetime.now(timezone.utc) - timedelta(days=_DAYS_J90)
    slug = article.slug or ""
    if not slug:
        return 0

    events = (
        db.query(TrafficEvent)
        .filter(
            TrafficEvent.project_id == article.project_id,
            TrafficEvent.created_at >= since,
        )
        .all()
    )
    return sum(1 for e in events if slug in (e.path or e.url))
