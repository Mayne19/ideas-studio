from __future__ import annotations

from typing import Any

from app.services.seo.eeat_service import compute_eeat_score
from app.services.seo.format_expectations import get_format
from app.services.seo.geo_expert_service import compute_geo_score
from app.services.seo.originality_service import compute_originality_score
from app.services.seo.readability_service import compute_readability_score


def _get(article: Any, field: str, default: Any = None) -> Any:
    if isinstance(article, dict):
        return article.get(field, default)
    return getattr(article, field, default)


def _to_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _get_geo_score(article: Any) -> float | None:
    geo = _get(article, "geo_optimization_json")
    if geo and isinstance(geo, dict):
        return _to_float(geo.get("geo_score"))
    return None


def _get_originality_score(article: Any) -> float | None:
    orig = _get(article, "originality_report_json")
    if orig and isinstance(orig, dict):
        v2 = orig.get("v2")
        if v2 and isinstance(v2, dict):
            return _to_float(v2.get("score"))
        return _to_float(orig.get("heuristic_score"))
    return None


def _get_eeat_score(article: Any) -> float | None:
    eeat_json = _get(article, "eeat_checklist_json")
    if eeat_json and isinstance(eeat_json, dict):
        v2 = eeat_json.get("v2")
        if v2 and isinstance(v2, dict):
            return _to_float(v2.get("score"))
        return _to_float(eeat_json.get("score"))
    return _to_float(_get(article, "eeat_score"))


def _get_readability_score(article: Any) -> float | None:
    rdbl = _get(article, "readability_report_json")
    if rdbl and isinstance(rdbl, dict):
        return _to_float(rdbl.get("score"))
    return _to_float(_get(article, "readability_score"))


def compute_global_score(article: Any) -> dict:
    """
    Scoring v2.1 — pondération : SEO 35% · EEAT 25% · Lisibilité 20% · Originalité 20%
    Le volume n'est jamais noté directement.
    """
    seo = _to_float(_get(article, "seo_score"))
    eeat = _get_eeat_score(article)
    readability = _get_readability_score(article)
    originality = _get_originality_score(article)
    geo = _get_geo_score(article)
    quality = _to_float(_get(article, "quality_score"))

    present: list[float] = []
    weights: list[int] = []

    if seo is not None:
        present.append(seo)
        weights.append(35)
    if eeat is not None:
        present.append(eeat)
        weights.append(25)
    if readability is not None:
        present.append(readability)
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
        incomplete_reason = "Aucun score disponible"

    # Blocking rules v2.1
    originality_report = _get(article, "originality_report_json")
    if originality_report and isinstance(originality_report, dict):
        v2 = originality_report.get("v2") or {}
        status = v2.get("status") or ""
        score_v2 = v2.get("score")
        if status == "unverified" and (score_v2 is None or score_v2 < 50):
            global_score_valid = False
            incomplete_reason = "Originalité non vérifiée — aucune source fournie"
        elif originality_report.get("manual_review_needed") and not status:
            global_score_valid = False
            incomplete_reason = "Originalité : révision manuelle requise"
    elif originality is None:
        global_score_valid = False
        if not incomplete_reason:
            incomplete_reason = "Originalité non vérifiée"

    if len(present) < 2:
        global_score_valid = False
        if not incomplete_reason:
            missing = []
            if seo is None: missing.append("SEO")
            if eeat is None: missing.append("EEAT")
            if readability is None: missing.append("Lisibilité")
            if originality is None: missing.append("Originalité")
            incomplete_reason = f"Scores manquants : {', '.join(missing)}"

    return {
        "global_score": global_score,
        "global_score_valid": global_score_valid,
        "incomplete_reason": incomplete_reason,
        "seo_contrib": seo,
        "eeat_contrib": eeat,
        "readability_contrib": readability,
        "originality_contrib": originality,
        "geo_contrib": geo,
        "quality_contrib": quality,
        "content_format": get_format(article),
        "scoring_note": "Scoring v2.1 — SEO×35% · EEAT×25% · Lisibilité×20% · Originalité×20%. Volume non noté.",
    }


def run_full_scoring(article: Any, project_articles: list[Any] | None = None) -> dict:
    """Run all scoring experts and return individual results."""
    return {
        "eeat": compute_eeat_score(article),
        "originality": compute_originality_score(article, project_articles or []),
        "readability": compute_readability_score(article),
        "geo": compute_geo_score(article),
    }


# ── Legacy helpers kept for backward compat ──────────────────────────────────

def _get_score(article: Any, field: str) -> float | None:
    return _to_float(_get(article, field))


def _get_json_field(article: Any, field: str) -> dict | None:
    val = _get(article, field)
    return val if isinstance(val, dict) else None
