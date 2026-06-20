from __future__ import annotations

from typing import Any


def compute_global_score(article: Any) -> dict:
    seo = _get_score(article, "seo_score")
    quality = _get_score(article, "quality_score")
    geo = _get_geo_score(article)
    originality = _get_originality_score(article)

    present = []
    weights = []

    if seo is not None:
        present.append(seo)
        weights.append(35)
    if quality is not None:
        present.append(quality)
        weights.append(25)
    if geo is not None:
        present.append(geo)
        weights.append(20)
    if originality is not None:
        present.append(originality)
        weights.append(20)

    total_weight = sum(weights)
    global_score: float | None = None
    global_score_valid = True
    incomplete_reason: str | None = None

    if total_weight > 0:
        global_score = round(sum(s * w for s, w in zip(present, weights)) / total_weight, 1)
    else:
        global_score = None
        global_score_valid = False
        incomplete_reason = "Aucun score disponible pour le calcul"

    originality_report = _get_json_field(article, "originality_report_json")
    if originality_report:
        trust_level = originality_report.get("trust_level") or (
            "medium" if originality_report.get("heuristic_score") is not None else "low"
        )
        manual_review = originality_report.get("manual_review_needed", False)
        if trust_level == "low" or manual_review:
            global_score_valid = False
            incomplete_reason = "Originalite non verifiable ou faible confiance"
    elif originality is None:
        global_score_valid = False
        if not incomplete_reason:
            incomplete_reason = "Originalite non verifiee"

    if len(present) < 4:
        global_score_valid = False
        if not incomplete_reason:
            missing = []
            if seo is None:
                missing.append("SEO")
            if quality is None:
                missing.append("Qualite")
            if geo is None:
                missing.append("GEO")
            if originality is None:
                missing.append("Originalite")
            incomplete_reason = f"Scores manquants: {', '.join(missing)}"

    return {
        "global_score": global_score,
        "global_score_valid": global_score_valid,
        "incomplete_reason": incomplete_reason,
        "seo_contrib": seo,
        "quality_contrib": quality,
        "geo_contrib": geo,
        "originality_contrib": originality,
        "scoring_note": "Score V1 calcule depuis SEO, qualite, GEO et originalite; certains signaux peuvent etre heuristiques.",
    }


def _get_score(article: Any, field: str) -> float | None:
    if isinstance(article, dict):
        val = article.get(field)
    else:
        val = getattr(article, field, None)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _get_geo_score(article: Any) -> float | None:
    geo = _get_json_field(article, "geo_optimization_json")
    if geo and isinstance(geo, dict):
        score = geo.get("geo_score")
        if score is not None:
            try:
                return float(score)
            except (TypeError, ValueError):
                return None
    return None


def _get_originality_score(article: Any) -> float | None:
    orig = _get_json_field(article, "originality_report_json")
    if orig and isinstance(orig, dict):
        score = orig.get("heuristic_score")
        if score is not None:
            try:
                return float(score)
            except (TypeError, ValueError):
                return None
    return None


def _get_json_field(article: Any, field: str) -> dict | None:
    if isinstance(article, dict):
        val = article.get(field)
    else:
        val = getattr(article, field, None)
    if val is None:
        return None
    if isinstance(val, dict):
        return val
    return None
