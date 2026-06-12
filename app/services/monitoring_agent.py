import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.article import Article
from app.models.notification import Notification
from app.services.log_service import log_step

logger = logging.getLogger(__name__)

MONITORING_INTERVALS = [
    timedelta(days=30),
    timedelta(days=60),
    timedelta(days=90),
    timedelta(days=180),
]


def _article_needs_review(article: Article, now: datetime) -> bool:
    """Check if a published article needs a monitoring review."""
    if article.monitoring_status in ("improvement_in_progress", "improvement_ready"):
        return False
    if article.next_review_at and article.next_review_at > now:
        return False
    if not article.published_at:
        return False
    return True


def _build_performance_diagnosis(article: Article) -> dict:
    """Build a performance diagnosis based on available data."""
    diagnosis = {
        "article_id": article.id,
        "title": article.title,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "age_days": (datetime.now(timezone.utc) - article.published_at).days if article.published_at else None,
        "seo_score": article.seo_score,
        "readability_score": article.readability_score,
        "quality_score": article.quality_score,
        "eeat_score": article.eeat_score,
        "traffic_data_available": False,
        "diagnosis": [],
    }

    # Check for low scores
    thresholds = [
        (article.seo_score, 70, "Score SEO faible ({score}/100). Optimiser le contenu pour les moteurs de recherche."),
        (article.readability_score, 60, "Score de lisibilité faible ({score}/100). Simplifier la structure des phrases."),
        (article.quality_score, 65, "Score qualité insuffisant ({score}/100). Enrichir le contenu."),
        (article.eeat_score, 60, "Score EEAT faible ({score}/100). Ajouter des signes d'expertise."),
    ]
    for score, threshold, template in thresholds:
        if score is not None and score < threshold:
            diagnosis["diagnosis"].append({
                "type": "low_score",
                "severity": "warning" if score >= threshold * 0.8 else "critical",
                "message": template.format(score=round(score)),
            })

    # Check age
    age_days = diagnosis["age_days"]
    if age_days and age_days > 180:
        diagnosis["diagnosis"].append({
            "type": "stale_content",
            "severity": "warning",
            "message": f"Article publié il y a {age_days} jours. Envisager une mise à jour du contenu.",
        })

    # Weekly views if available
    if article.search_console_metrics_json:
        try:
            metrics = json.loads(article.search_console_metrics_json)
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
        except (json.JSONDecodeError, TypeError):
            pass

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
    if not article or article.status != "published":
        return None

    diagnosis = _build_performance_diagnosis(article)
    proposal = _build_improvement_proposal(diagnosis)

    article.performance_diagnosis_json = diagnosis
    article.improvement_proposal_json = proposal
    article.monitoring_status = "proposed"
    article.improvement_reason = proposal.get("summary", "")
    article.next_review_at = datetime.now(timezone.utc) + timedelta(days=90)

    log_step(
        db, article.project_id,
        f"Analyse monitoring pour {article.title} : {len(diagnosis.get('diagnosis', []))} pistes identifiées",
        level="info", step="monitoring_agent", article_id=article.id,
    )

    db.flush()
    return article


def scan_for_review(db: Session, project_id: str | None = None) -> list[Article]:
    """Scan all published articles that need a monitoring review."""
    now = datetime.now(timezone.utc)
    query = select(Article).where(Article.status == "published")

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
            except Exception as exc:
                logger.exception("Failed to analyze article %s for improvement", article.id)

    if reviewed:
        db.commit()
        for a in reviewed:
            db.refresh(a)
    return reviewed


def create_improvement_draft(db: Session, article_id: str) -> Article | None:
    """Create an improvement draft (new article revision) from a monitoring proposal."""
    article = db.get(Article, article_id)
    if not article or article.monitoring_status not in ("proposed", "accepted"):
        return None

    revision = Article(
        id=str(uuid.uuid4()),
        project_id=article.project_id,
        category_id=article.category_id,
        title=f"[Amélioration] {article.title}",
        slug=f"improve-{uuid.uuid4().hex[:8]}",
        content=article.content,
        status="improvement_proposed",
        keyword=article.keyword,
        audience=article.audience,
        angle=article.angle,
        search_intent=article.search_intent,
        opportunity_score=article.opportunity_score,
        priority=article.priority,
        original_article_id=article.id,
        improvement_reason=article.improvement_reason,
        improvement_proposal_json=article.improvement_proposal_json,
        performance_diagnosis_json=article.performance_diagnosis_json,
        monitoring_status="in_progress",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    # Mark original as having improvement in progress
    article.monitoring_status = "improvement_in_progress"

    db.add(revision)
    log_step(
        db, article.project_id,
        f"Proposition d'amélioration créée pour {article.title} : révision {revision.id}",
        level="info", step="monitoring_agent", article_id=article.id,
    )
    db.flush()
    return revision
