from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai import Pipeline, WorkflowRun
from app.models.content import Article, ArticleKeyword, ArticleRevision, ArticleSeo, Keyword
from app.models.reference import ArticleStatus, KeywordRole, RunStatus, set_article_status
from app.services.scoring_service import compute_global_score
from app.services.seo.artifacts import get_latest_artifacts


def _load_validation_context(db: Session, article: Article) -> dict[str, Any]:
    """Rassemble en un seul passage tout ce que compute_critical_warnings et
    check_validation_thresholds lisaient auparavant sur le modèle plat."""
    revision = None
    if article.current_revision_id:
        revision = db.get(ArticleRevision, article.current_revision_id)
    seo = db.get(ArticleSeo, article.id)
    keyword_term = db.execute(
        select(Keyword.term)
        .join(ArticleKeyword, ArticleKeyword.keyword_id == Keyword.id)
        .where(ArticleKeyword.article_id == article.id, ArticleKeyword.role == KeywordRole.PRIMARY)
    ).scalar_one_or_none()

    artifacts = get_latest_artifacts(
        db, article.id, ["originality_report", "sources", "estimated_cost", "fact_check_report"]
    )
    latest_run = db.execute(
        select(WorkflowRun).where(WorkflowRun.article_id == article.id).order_by(WorkflowRun.started_at.desc()).limit(1)
    ).scalar_one_or_none()
    pipeline = db.get(Pipeline, article.project_id)

    return {
        "content": revision.body if revision else "",
        "title": revision.title if revision else "",
        "meta_title": seo.meta_title if seo else "",
        "meta_description": seo.meta_description if seo else "",
        "keyword": keyword_term or "",
        "originality_report": artifacts.get("originality_report"),
        "sources": artifacts.get("sources"),
        "estimated_cost": artifacts.get("estimated_cost"),
        "fact_check": artifacts.get("fact_check_report"),
        "workflow_failed": bool(latest_run and latest_run.status_reason_id == RunStatus.FAILED),
        "workflow_incomplete": bool(
            latest_run and latest_run.status_reason_id in (RunStatus.QUEUED, RunStatus.RUNNING)
        ),
        "cost_limit_eur": float(pipeline.cost_limit_per_article) if pipeline and pipeline.cost_limit_per_article else None,
        "scheduled_for": article.scheduled_for,
    }


def compute_critical_warnings(ctx: dict[str, Any]) -> list[dict]:
    warnings: list[dict] = []

    content = ctx["content"] or ""
    originality_report = ctx["originality_report"]
    sources = ctx["sources"]

    if not sources:
        warnings.append({
            "type": "missing_sources",
            "severity": "warning",
            "message": "Aucune source fournie pour verifier les affirmations importantes.",
        })

    if originality_report is None:
        warnings.append({
            "type": "originality_not_verified",
            "severity": "critical",
            "message": "Originalite non verifiee. Lancez une analyse d'originalite.",
        })

    if originality_report:
        trust = originality_report.get("trust_level") or (
            "medium" if originality_report.get("heuristic_score") is not None else "low"
        )
        manual = originality_report.get("manual_review_needed", False)
        if trust == "low":
            warnings.append({
                "type": "originality_low_trust",
                "severity": "critical",
                "message": "Originalite a faible confiance. Verifiez manuellement.",
            })
        if manual:
            warnings.append({
                "type": "originality_review_needed",
                "severity": "critical",
                "message": "Relecture d'originalite requise.",
            })
        suspicious = originality_report.get("suspicious_passages", [])
        if suspicious:
            warnings.append({
                "type": "content_too_close_to_source",
                "severity": "critical",
                "message": f"{len(suspicious)} passage(s) suspects d'etre trop proches des sources.",
            })

    if not ctx["meta_title"]:
        warnings.append({
            "type": "missing_meta_title", "severity": "critical",
            "message": "Le meta title est absent.",
        })
    if not ctx["meta_description"]:
        warnings.append({
            "type": "missing_meta_description", "severity": "critical",
            "message": "La meta description est absente.",
        })

    if content:
        h1_count = len(re.findall(r"<h1[^>]*>", content, re.IGNORECASE))
        if h1_count == 0:
            warnings.append({
                "type": "missing_h1", "severity": "critical",
                "message": "L'article n'a pas de H1.",
            })
        elif h1_count > 1:
            warnings.append({
                "type": "multiple_h1", "severity": "warning",
                "message": f"L'article contient {h1_count} H1.",
            })

    word_count = len(re.findall(r"\b\w+\b", content)) if content else 0
    if word_count < 300:
        warnings.append({
            "type": "article_too_short", "severity": "critical",
            "message": f"Article trop court ({word_count} mots). Minimum 300 mots requis.",
        })

    estimated_cost = ctx["estimated_cost"]
    if estimated_cost and ctx["cost_limit_eur"] is not None:
        cost_eur = estimated_cost.get("estimated_cost_eur")
        if cost_eur is not None and float(cost_eur) > ctx["cost_limit_eur"]:
            warnings.append({
                "type": "cost_exceeded", "severity": "critical",
                "message": f"Cout estime ({float(cost_eur):.4f} EUR) depasse la limite ({ctx['cost_limit_eur']:.4f} EUR).",
            })

    if ctx["workflow_failed"]:
        warnings.append({
            "type": "agent_error", "severity": "critical",
            "message": "Une erreur agent non resolue persiste.",
        })

    fact_check = ctx["fact_check"]
    if fact_check and fact_check.get("status") == "failed":
        warnings.append({
            "type": "fact_check_failed", "severity": "critical",
            "message": "Le fact-check a echoue.",
        })

    if ctx["scheduled_for"] is None:
        warnings.append({
            "type": "missing_publish_date", "severity": "critical",
            "message": "Aucune date de publication prevue.",
        })

    if ctx["workflow_incomplete"]:
        warnings.append({
            "type": "incomplete_workflow", "severity": "critical",
            "message": "Le workflow n'est pas termine.",
        })

    return warnings


def check_validation_thresholds(db: Session, article: Article, planned_publish_at=None) -> dict:
    scoring = compute_global_score(db, article.id, article=article)
    global_score = scoring["global_score"]
    global_score_valid = scoring["global_score_valid"]
    seo_contrib = scoring["seo_contrib"]
    quality = scoring["quality_contrib"]
    geo = scoring["geo_contrib"]
    originality = scoring["originality_contrib"]

    ctx = _load_validation_context(db, article)
    if planned_publish_at is not None:
        ctx["scheduled_for"] = planned_publish_at
    warnings = compute_critical_warnings(ctx)

    blocking_reasons: list[str] = []
    non_blocking_warnings: list[dict] = []

    if not global_score_valid:
        blocking_reasons.append(scoring.get("incomplete_reason", "Score global incomplet"))
    elif global_score is not None and global_score < 90:
        blocking_reasons.append(f"Score global ({global_score}) < 90")

    if seo_contrib is not None and seo_contrib < 85:
        blocking_reasons.append(f"Score SEO ({seo_contrib}) < 85")
    if quality is not None and quality < 85:
        blocking_reasons.append(f"Score Qualite ({quality}) < 85")
    if geo is not None and geo < 80:
        blocking_reasons.append(f"Score GEO ({geo}) < 80")
    if originality is not None and originality < 85:
        blocking_reasons.append(f"Score Originalite ({originality}) < 85")

    for w in warnings:
        if w["severity"] == "critical":
            blocking_reasons.append(w["message"])
        else:
            non_blocking_warnings.append(w)

    return {
        "valid": len(blocking_reasons) == 0,
        "global_score": global_score,
        "global_score_valid": global_score_valid,
        "reasons": blocking_reasons,
        "warnings": non_blocking_warnings,
        "critical_warnings": [w for w in warnings if w["severity"] == "critical"],
    }


def validate_bulk_articles(db: Session, project_id: str, article_ids: list[str]) -> dict:
    articles = db.execute(
        select(Article).where(Article.id.in_(article_ids), Article.project_id == project_id)
    ).scalars().all()

    found_ids = {a.id for a in articles}
    not_found = [aid for aid in article_ids if aid not in found_ids]

    validated_count = 0
    blocked_count = 0
    blocked_articles: list[dict] = []
    to_schedule: list[Article] = []

    for article in articles:
        result = check_validation_thresholds(db, article)
        if result["valid"]:
            validated_count += 1
            to_schedule.append(article)
        else:
            blocked_count += 1
            blocked_articles.append({
                "article_id": article.id,
                "title": article.current_revision.title if article.current_revision_id else "",
                "reasons": result["reasons"],
            })

    scheduled_count = 0
    for article in to_schedule:
        if article.scheduled_for is None:
            blocked_count += 1
            validated_count -= 1
            blocked_articles.append({
                "article_id": article.id,
                "reasons": ["Aucune date de publication prevue."],
            })
            continue
        from app.models.content import ArticleScore
        scoring = compute_global_score(db, article.id, article=article)
        db.add(ArticleScore(
            article_id=article.id,
            global_score=scoring["global_score"],
            seo_score=scoring["seo_contrib"],
            eeat_score=scoring["eeat_contrib"],
            readability_score=scoring["readability_contrib"],
            geo_score=scoring["geo_contrib"],
        ))
        # "scheduled" ne requiert pas de published_revision_id — voir ref.article_status_reasons.
        set_article_status(article, ArticleStatus.SCHEDULED)
        article.updated_at = datetime.now(timezone.utc)
        scheduled_count += 1

    if to_schedule:
        db.commit()

    return {
        "validated_count": validated_count,
        "blocked_count": blocked_count,
        "scheduled_count": scheduled_count,
        "not_found_count": len(not_found),
        "not_found_ids": not_found,
        "blocked_articles": blocked_articles,
    }
