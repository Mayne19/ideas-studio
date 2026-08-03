import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.content import Article, ArticleRevision
from app.models.reference import ArticleStatus, RevisionSource, set_article_status
from app.services.log_service import log_step
from app.services.seo.artifacts import get_latest_artifact, save_artifact

logger = logging.getLogger(__name__)

MONITORING_INTERVALS = [
    timedelta(days=30),
    timedelta(days=60),
    timedelta(days=90),
    timedelta(days=180),
]

_ACTIVE_MONITORING_STATUSES = (ArticleStatus.IMPROVEMENT_IN_PROGRESS, ArticleStatus.IMPROVEMENT_READY)


def _article_needs_review(article: Article, now: datetime) -> bool:
    """Check if a published article needs a monitoring review."""
    if article.status_reason_id in _ACTIVE_MONITORING_STATUSES:
        return False
    if article.next_review_at and article.next_review_at > now:
        return False
    if not article.published_at:
        return False
    return True


def _build_performance_diagnosis(db: Session, article: Article) -> dict:
    """Build a performance diagnosis based on available data."""
    from app.models.content import ArticleScore
    revision = article.current_revision
    latest_score = db.execute(
        select(ArticleScore)
        .where(ArticleScore.article_id == article.id)
        .order_by(ArticleScore.evaluated_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    seo_score = float(latest_score.seo_score) if latest_score and latest_score.seo_score is not None else None
    readability_score = float(latest_score.readability_score) if latest_score and latest_score.readability_score is not None else None
    quality_score = float(latest_score.quality_score) if latest_score and latest_score.quality_score is not None else None
    eeat_score = float(latest_score.eeat_score) if latest_score and latest_score.eeat_score is not None else None

    diagnosis = {
        "article_id": article.id,
        "title": revision.title if revision else "",
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "age_days": (datetime.now(timezone.utc) - article.published_at).days if article.published_at else None,
        "seo_score": seo_score,
        "readability_score": readability_score,
        "quality_score": quality_score,
        "eeat_score": eeat_score,
        "traffic_data_available": False,
        "diagnosis": [],
    }

    thresholds = [
        (seo_score, 70, "Score SEO faible ({score}/100). Optimiser le contenu pour les moteurs de recherche."),
        (readability_score, 60, "Score de lisibilité faible ({score}/100). Simplifier la structure des phrases."),
        (quality_score, 65, "Score qualité insuffisant ({score}/100). Enrichir le contenu."),
        (eeat_score, 60, "Score EEAT faible ({score}/100). Ajouter des signes d'expertise."),
    ]
    for score, threshold, template in thresholds:
        if score is not None and score < threshold:
            diagnosis["diagnosis"].append({
                "type": "low_score",
                "severity": "warning" if score >= threshold * 0.8 else "critical",
                "message": template.format(score=round(score)),
            })

    age_days = diagnosis["age_days"]
    if age_days and age_days > 180:
        diagnosis["diagnosis"].append({
            "type": "stale_content",
            "severity": "warning",
            "message": f"Article publié il y a {age_days} jours. Envisager une mise à jour du contenu.",
        })

    metrics = get_latest_artifact(db, article.id, "search_console_metrics")
    if isinstance(metrics, dict):
        diagnosis["traffic_data_available"] = True
        clicks = metrics.get("clicks", 0)
        impressions = metrics.get("impressions", 0)
        if impressions and clicks:
            ctr = clicks / impressions * 100
            if ctr < 1:
                diagnosis["diagnosis"].append({
                    "type": "low_ctr",
                    "severity": "warning",
                    "message": f"CTR très faible ({ctr:.1f}%). Optimiser le titre et la meta description.",
                })
        if clicks is not None and clicks < 5:
            diagnosis["diagnosis"].append({
                "type": "low_traffic",
                "severity": "critical",
                "message": "Trafic très faible. Envisager une révision complète de l'article.",
            })

    if not diagnosis["diagnosis"]:
        diagnosis["diagnosis"].append({
            "type": "good_performance",
            "severity": "info",
            "message": "L'article semble bien performant pour le moment. Aucune action urgente requise.",
        })

    return diagnosis


def _build_improvement_proposal(diagnosis: dict) -> dict:
    """Build an improvement proposal based on the diagnosis."""
    proposal = {
        "summary": "",
        "suggested_actions": [],
        "priority": "low",
        "estimated_effort": "low",
    }

    critical_items = [d for d in diagnosis.get("diagnosis", []) if d.get("severity") == "critical"]
    warning_items = [d for d in diagnosis.get("diagnosis", []) if d.get("severity") == "warning"]

    if critical_items:
        proposal["priority"] = "high"
        proposal["estimated_effort"] = "high"
        proposal["summary"] = "L'article nécessite des améliorations urgentes pour maintenir sa performance."
    elif warning_items:
        proposal["priority"] = "medium"
        proposal["estimated_effort"] = "medium"
        proposal["summary"] = "Quelques axes d'amélioration identifiés pour renforcer la performance de l'article."
    else:
        proposal["summary"] = "Aucune amélioration majeure requise pour le moment."

    for d in diagnosis.get("diagnosis", []):
        if d.get("type") in ("low_score", "stale_content", "low_ctr", "low_traffic"):
            proposal["suggested_actions"].append({
                "type": d["type"],
                "description": d["message"],
                "action": "create_revision",
            })

    return proposal


def analyze_article_for_improvement(db: Session, article_id: str) -> Article | None:
    """Analyze a published article and create an improvement proposal if needed."""
    article = db.get(Article, article_id)
    if not article or article.status_reason_id != ArticleStatus.PUBLISHED:
        return None

    diagnosis = _build_performance_diagnosis(db, article)
    proposal = _build_improvement_proposal(diagnosis)

    save_artifact(db, article.id, "performance_diagnosis", diagnosis)
    save_artifact(db, article.id, "improvement_proposal", proposal)
    article.next_review_at = datetime.now(timezone.utc) + timedelta(days=90)

    revision = article.current_revision
    log_step(
        db, article.project_id,
        f"Analyse monitoring pour {revision.title if revision else article.id} : {len(diagnosis.get('diagnosis', []))} pistes identifiées",
        level="info", step="monitoring_agent", article_id=article.id,
    )

    db.flush()
    return article


def scan_for_review(db: Session, project_id: str | None = None) -> list[Article]:
    """Scan all published articles that need a monitoring review."""
    now = datetime.now(timezone.utc)
    query = select(Article).where(Article.status_reason_id == ArticleStatus.PUBLISHED)

    if project_id:
        query = query.where(Article.project_id == project_id)

    articles = db.execute(query).scalars().all()
    reviewed = []

    for article in articles:
        if _article_needs_review(article, now):
            try:
                result = analyze_article_for_improvement(db, article.id)
                if result:
                    reviewed.append(result)
            except Exception:
                logger.exception("Failed to analyze article %s for improvement", article.id)

    if reviewed:
        db.commit()
        for a in reviewed:
            db.refresh(a)
    return reviewed


def create_improvement_draft(db: Session, article_id: str) -> ArticleRevision | None:
    """Crée une nouvelle révision (pas un nouvel article) portant la proposition
    d'amélioration — content.article_revisions couvre déjà ce besoin nativement,
    voir REPRENDRE-LA-MAIN.md §6 étape 6 (historique = révisions, pas des lignes
    articles dupliquées avec original_article_id)."""
    article = db.get(Article, article_id)
    if not article:
        return None
    proposal = get_latest_artifact(db, article.id, "improvement_proposal")
    if not proposal or article.status_reason_id in _ACTIVE_MONITORING_STATUSES:
        return None

    current = article.current_revision
    if current is None:
        return None

    last_no = db.execute(
        select(ArticleRevision.revision_no)
        .where(ArticleRevision.article_id == article.id)
        .order_by(ArticleRevision.revision_no.desc())
        .limit(1)
    ).scalar_one_or_none() or 0

    draft = ArticleRevision(
        article_id=article.id,
        revision_no=last_no + 1,
        source=RevisionSource.AI,
        title=current.title,
        excerpt=current.excerpt,
        body=current.body,
        blocks=current.blocks,
        faq=current.faq,
        callouts=current.callouts,
        word_count=current.word_count,
        reading_time_minutes=current.reading_time_minutes,
    )
    db.add(draft)
    db.flush()

    article.current_revision_id = draft.id
    set_article_status(article, ArticleStatus.IMPROVEMENT_IN_PROGRESS)
    article.updated_at = datetime.now(timezone.utc)

    log_step(
        db, article.project_id,
        f"Proposition d'amélioration créée pour {current.title} : révision {draft.id}",
        level="info", step="monitoring_agent", article_id=article.id,
    )
    db.flush()
    return draft
