"""Rédacteur local (phase 3 de la refonte) : ce dont le rédacteur sur le Mac a
besoin pour travailler, autour des routes du parcours éditorial.

- les sujets à rédiger (statut « en rédaction ») avec leur demande ;
- les articles publiés du site (titre, URL, résumé) pour le maillage interne ;
- l'enregistrement du rapport du rédacteur (coût réel, jetons, erreur).

Le dépôt de l'article passe par la route de dépôt du parcours éditorial.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Article, ArticleRevision
from app.models.core import Project
from app.models.reference import ArticleStatus
from app.services.editorial_workflow_service import EditorialStatus, workflow_status
from app.services.seo.artifacts import get_latest_artifact, save_artifact

WRITER_REPORT_ARTIFACT_KEY = "editorial_writer_report"
REQUEST_ARTIFACT_KEY = "editorial_request"
SITE_ARTICLES_LIMIT = 60


def writing_jobs(db: Session, project_id: str) -> list[dict]:
    """Sujets en rédaction, du plus ancien au plus récent."""
    articles = db.execute(
        select(Article).where(Article.project_id == project_id).order_by(Article.updated_at.asc())
    ).scalars().all()
    jobs = []
    for article in articles:
        if workflow_status(article) != EditorialStatus.WRITING:
            continue
        request = get_latest_artifact(db, article.id, REQUEST_ARTIFACT_KEY) or {}
        revision = article.current_revision
        jobs.append({
            "article_id": article.id,
            "subject": (revision.title if revision else "") or request.get("keyword") or article.slug,
            "keyword": request.get("keyword"),
            "context": request.get("context_hint"),
            "audience": request.get("audience"),
            "angle": request.get("angle"),
            "comment": request.get("comment"),
        })
    return jobs


def site_articles(db: Session, project_id: str) -> list[dict]:
    """Articles publiés (titre, URL, résumé) transmis au skill pour le maillage."""
    from app.services.seo.internal_link_service import _extract_excerpt

    project = db.get(Project, project_id)
    if project is None or not project.domain:
        return []
    base = project.domain if project.domain.startswith("http") else f"https://{project.domain}"
    rows = db.execute(
        select(Article, ArticleRevision.title)
        .join(ArticleRevision, ArticleRevision.id == Article.current_revision_id)
        .where(Article.project_id == project_id, Article.status_reason_id == ArticleStatus.PUBLISHED)
        .order_by(Article.published_at.desc())
        .limit(SITE_ARTICLES_LIMIT)
    ).all()
    return [{"titre": title, "url": f"{base.rstrip('/')}/blog/{article.slug}", "resume": _extract_excerpt(article, title)}
            for article, title in rows if article.slug and title]


def record_writer_report(db: Session, article: Article, report: dict) -> dict:
    """Coût réel, jetons, durée ou erreur du rédacteur, consultables dans le CMS."""
    payload = {key: report.get(key) for key in ("cost_usd", "tokens", "duration_s", "turns", "error", "checks")
               if key in report}
    save_artifact(db, article.id, WRITER_REPORT_ARTIFACT_KEY, payload)
    db.commit()
    return payload
