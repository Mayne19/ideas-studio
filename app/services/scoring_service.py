from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import ArticleScore
from app.services.seo.artifacts import get_latest_artifacts
from app.services.seo.eeat_service import compute_eeat_score
from app.services.seo.format_expectations import get_format
from app.services.seo.geo_expert_service import compute_geo_score
from app.services.seo.originality_service import compute_originality_score
from app.services.seo.readability_service import compute_readability_score


def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _latest_article_score(db: Session, article_id: str) -> ArticleScore | None:
    return db.execute(
        select(ArticleScore)
        .where(ArticleScore.article_id == article_id)
        .order_by(ArticleScore.evaluated_at.desc())
        .limit(1)
    ).scalar_one_or_none()


_UNSET = object()


def compute_global_score(
    db: Session, article_id: str, article=None,
    *, latest_score: "ArticleScore | None" = _UNSET, artifacts: dict | None = None,
) -> dict:
    """
    Scoring v2.1 — pondération : SEO 35% · EEAT 25% · Lisibilité 20% · Originalité 20%
    Le volume n'est jamais noté directement.

    `article` (optionnel) : objet content.Article, uniquement pour get_format()
    qui a besoin de content_format/target_word_count — sans dépendance sur les
    scores eux-mêmes, qui viennent tous de la base (article_scores + artifacts).

    `latest_score`/`artifacts` (optionnels) : permet d'injecter des données déjà
    chargées en masse pour plusieurs articles (voir to_public_batch) au lieu de
    refaire une requête individuelle par article — même calcul, juste sans le N+1.
    """
    if latest_score is _UNSET:
        latest_score = _latest_article_score(db, article_id)
    quality = _to_float(latest_score.quality_score) if latest_score else None

    if artifacts is None:
        artifacts = get_latest_artifacts(
            db, article_id,
            ["eeat_checklist", "readability_report", "originality_report", "geo_optimization",
             "seo_final_checklist", "human_presence_report"],
        )
    eeat_json = artifacts.get("eeat_checklist")
    readability_json = artifacts.get("readability_report")
    originality_report = artifacts.get("originality_report")
    geo_json = artifacts.get("geo_optimization")
    seo_json = artifacts.get("seo_final_checklist")
    human_presence_json = artifacts.get("human_presence_report")

    # seo_score n'est jamais peuplé directement sur article_scores par un agent
    # dédié (contrairement à eeat/readability/geo) : il vient toujours de
    # l'artifact seo_final_checklist, avec la ligne article_scores en repli
    # pour les scores historiques calculés avant que ce lien n'existe.
    seo = _to_float(seo_json.get("score")) if seo_json else None
    if seo is None:
        seo = _to_float(latest_score.seo_score) if latest_score else None

    eeat = None
    if eeat_json:
        v2 = eeat_json.get("v2") if isinstance(eeat_json.get("v2"), dict) else None
        eeat = _to_float(v2.get("score")) if v2 else _to_float(eeat_json.get("score"))
    if eeat is None:
        eeat = _to_float(latest_score.eeat_score) if latest_score else None

    readability = None
    if readability_json:
        readability = _to_float(readability_json.get("score"))
    if readability is None:
        readability = _to_float(latest_score.readability_score) if latest_score else None

    originality = None
    if originality_report:
        v2 = originality_report.get("v2") if isinstance(originality_report.get("v2"), dict) else None
        originality = _to_float(v2.get("score")) if v2 else _to_float(originality_report.get("heuristic_score"))

    geo = _to_float(geo_json.get("geo_score")) if geo_json else None
    human_presence = _to_float(human_presence_json.get("score")) if human_presence_json else None

    present: list[float] = []
    weights: list[int] = []

    # v2.2 — ajout Présence humaine (15%) : détecte spécifiquement les
    # phrases génériques, tirets cadratins, régularité mécanique des
    # paragraphes et absence de position tranchée — signaux qu'aucun des 4
    # scores existants ne capture directement (voir human_presence_service.py,
    # issu du guide de rédaction éditorial checklist qualité 90+). Poids
    # repris sur SEO/EEAT/Lisibilité/Originalité pour garder un total à 100%.
    if seo is not None:
        present.append(seo)
        weights.append(30)
    if eeat is not None:
        present.append(eeat)
        weights.append(20)
    if readability is not None:
        present.append(readability)
        weights.append(17)
    if originality is not None:
        present.append(originality)
        weights.append(18)
    if human_presence is not None:
        present.append(human_presence)
        weights.append(15)

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

    # Règles bloquantes v2.1
    if originality_report:
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
            if human_presence is None: missing.append("Présence humaine")
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
        "human_presence_contrib": human_presence,
        "content_format": get_format(article) if article is not None else None,
        "scoring_note": "Scoring v2.2 — SEO×30% · EEAT×20% · Lisibilité×17% · Originalité×18% · Présence humaine×15%. Volume non noté.",
    }


def run_full_scoring(article, project_articles: list | None = None) -> dict:
    """Exécute les experts de scoring heuristiques (ne touchent pas la base ;
    les résultats doivent être persistés séparément via save_artifact)."""
    return {
        "eeat": compute_eeat_score(article),
        "originality": compute_originality_score(article, project_articles or []),
        "readability": compute_readability_score(article),
        "geo": compute_geo_score(article),
    }
