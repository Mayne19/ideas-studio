from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.models.article import Article
from app.services.scoring_service import compute_global_score


def compute_critical_warnings(article: Any, planned_publish_at=None) -> list[dict]:
    warnings: list[dict] = []

    content = _get_str(article, "content", "")
    title = _get_str(article, "title", "")
    meta_title = _get_str(article, "meta_title", "")
    meta_description = _get_str(article, "meta_description", "")
    keyword = _get_str(article, "keyword", "")
    slug = _get_str(article, "slug", "")

    # Source manquante pour affirmation importante
    originality_report = _get_json(article, "originality_report_json")
    sources = _get_json(article, "sources_json")
    if sources is None or not sources:
        warnings.append({
            "type": "missing_sources",
            "severity": "warning",
            "message": "Aucune source fournie pour verifier les affirmations importantes.",
        })

    # Originalite non verifiee
    if originality_report is None:
        warnings.append({
            "type": "originality_not_verified",
            "severity": "critical",
            "message": "Originalite non verifiee. Lancez une analyse d'originalite.",
        })

    # Originalite a faible confiance
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

    # Contenu trop proche d'une source
    if originality_report:
        suspicious = originality_report.get("suspicious_passages", [])
        if suspicious and len(suspicious) > 0:
            warnings.append({
                "type": "content_too_close_to_source",
                "severity": "critical",
                "message": f"{len(suspicious)} passage(s) suspects d'etre trop proches des sources.",
            })

    # Meta title absent
    if not meta_title:
        warnings.append({
            "type": "missing_meta_title",
            "severity": "critical",
            "message": "Le meta title est absent.",
        })

    # Meta description absente
    if not meta_description:
        warnings.append({
            "type": "missing_meta_description",
            "severity": "critical",
            "message": "La meta description est absente.",
        })

    # H1 absent ou multiple
    if content:
        import re
        h1_count = len(re.findall(r"<h1[^>]*>", content, re.IGNORECASE))
        if h1_count == 0:
            warnings.append({
                "type": "missing_h1",
                "severity": "critical",
                "message": "L'article n'a pas de H1.",
            })
        elif h1_count > 1:
            warnings.append({
                "type": "multiple_h1",
                "severity": "warning",
                "message": f"L'article contient {h1_count} H1.",
            })

    # Article incomplet
    word_count = 0
    if content:
        import re
        word_count = len(re.findall(r"\b\w+\b", content))
    if word_count < 300:
        warnings.append({
            "type": "article_too_short",
            "severity": "critical",
            "message": f"Article trop court ({word_count} mots). Minimum 300 mots requis.",
        })

    # Cout depasse
    estimated_cost = _get_json(article, "estimated_cost_json")
    if estimated_cost:
        cost_limit = _get_pipeline_cost_limit(article)
        cost_eur = estimated_cost.get("estimated_cost_eur")
        if cost_eur is not None and cost_limit is not None and float(cost_eur) > float(cost_limit):
            warnings.append({
                "type": "cost_exceeded",
                "severity": "critical",
                "message": f"Cout estime ({cost_eur:.4f} EUR) depasse la limite ({cost_limit:.4f} EUR).",
            })

    # Erreur agent non resolue
    workflow_status = _get_str(article, "workflow_status")
    if workflow_status == "failed":
        warnings.append({
            "type": "agent_error",
            "severity": "critical",
            "message": "Une erreur agent non resolue persiste.",
        })

    # Fact-check echoue
    fact_check = _get_json(article, "fact_check_report_json")
    if fact_check:
        fact_status = fact_check.get("status", "")
        if fact_status == "failed":
            warnings.append({
                "type": "fact_check_failed",
                "severity": "critical",
                "message": "Le fact-check a echoue.",
            })

    # Date de publication absente
    scheduled_at = planned_publish_at or _get_attr(article, "scheduled_at")
    if scheduled_at is None:
        warnings.append({
            "type": "missing_publish_date",
            "severity": "critical",
            "message": "Aucune date de publication prevue.",
        })

    # Agent obligatoire non termine
    completed = _get_str(article, "completed_agent_keys", "")
    if completed and not completed.endswith("__complete__"):
        warnings.append({
            "type": "incomplete_workflow",
            "severity": "critical",
            "message": "Le workflow n'est pas termine.",
        })

    return warnings


def check_validation_thresholds(article: Any, planned_publish_at=None) -> dict:
    scoring = compute_global_score(article)
    global_score = scoring["global_score"]
    global_score_valid = scoring["global_score_valid"]
    seo = scoring["seo_contrib"]
    quality = scoring["quality_contrib"]
    geo = scoring["geo_contrib"]
    originality = scoring["originality_contrib"]

    warnings = compute_critical_warnings(article, planned_publish_at=planned_publish_at)
    blocking_reasons: list[str] = []
    non_blocking_warnings: list[dict] = []

    # Check thresholds
    if not global_score_valid:
        blocking_reasons.append(scoring.get("incomplete_reason", "Score global incomplet"))
    elif global_score is not None and global_score < 90:
        blocking_reasons.append(f"Score global ({global_score}) < 90")

    if seo is not None and seo < 85:
        blocking_reasons.append(f"Score SEO ({seo}) < 85")
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


def validate_bulk_articles(db_session, project_id: str, article_ids: list[str]) -> dict:
    from sqlalchemy.orm import Session
    db: Session = db_session

    articles = db.query(Article).filter(
        Article.id.in_(article_ids),
        Article.project_id == project_id,
    ).all()

    found_ids = {a.id for a in articles}
    not_found = [aid for aid in article_ids if aid not in found_ids]

    validated_count = 0
    blocked_count = 0
    blocked_articles: list[dict] = []
    to_schedule: list[Article] = []

    for article in articles:
        result = check_validation_thresholds(article)
        if result["valid"]:
            validated_count += 1
            to_schedule.append(article)
        else:
            blocked_count += 1
            blocked_articles.append({
                "article_id": article.id,
                "title": article.title,
                "reasons": result["reasons"],
            })

    scheduled_count = 0
    for article in to_schedule:
        scheduled_at = article.scheduled_at
        if scheduled_at is None:
            blocked_count += 1
            validated_count -= 1
            blocked_articles.append({
                "article_id": article.id,
                "title": article.title,
                "reasons": ["Aucune date de publication prevue."],
            })
            continue
        scoring = compute_global_score(article)
        article.global_score = scoring["global_score"]
        article.global_score_valid = 1 if scoring["global_score_valid"] else 0
        article.status = "scheduled"
        article.scheduled_at = scheduled_at
        article.human_validated_at = datetime.now(timezone.utc)
        scheduled_count += 1

    if to_schedule:
        db.commit()
        for article in to_schedule:
            db.refresh(article)

    return {
        "validated_count": validated_count,
        "blocked_count": blocked_count,
        "scheduled_count": scheduled_count,
        "not_found_count": len(not_found),
        "not_found_ids": not_found,
        "blocked_articles": blocked_articles,
    }


def _get_str(article: Any, field: str, default: str = "") -> str:
    if isinstance(article, dict):
        val = article.get(field, default)
    else:
        val = getattr(article, field, default)
    return val if val is not None else default


def _get_attr(article: Any, field: str):
    if isinstance(article, dict):
        return article.get(field)
    return getattr(article, field, None)


def _get_json(article: Any, field: str) -> dict | None:
    if isinstance(article, dict):
        val = article.get(field)
    else:
        val = getattr(article, field, None)
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    return None


def _get_pipeline_cost_limit(article: Any) -> float | None:
    from sqlalchemy.orm import Session
    project_id = _get_str(article, "project_id")
    if not project_id:
        return None
    from app.core.database import SessionLocal
    from app.models.pipeline import ProjectPipeline
    db = SessionLocal()
    try:
        pipe = db.query(ProjectPipeline).filter(ProjectPipeline.project_id == project_id).first()
        if pipe:
            return pipe.cost_limit_per_article_eur
        return None
    finally:
        db.close()
