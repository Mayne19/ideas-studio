from __future__ import annotations

"""Agent réviseur — applique la grille de scoring à 10 critères (100 points)
et les 6 tests structurels universels avant soumission à l'éditeur humain
(voir docs/guide_formation_ia.md et docs/guide_tests_universels.md).

Réutilise les détecteurs déjà écrits dans human_presence_service.py et
content_structure_guard.py plutôt que de dupliquer la logique de
détection — ce module orchestre et reformate en grille de scoring +
rapport structuré, il n'invente pas de nouveaux signaux pour les critères
qui existent déjà. 100% heuristique sauf le critère "Moment de surprise",
qui nécessite un vrai jugement (voir sa docstring).
"""

import re

from app.services.seo.content_structure_guard import check_style_compliance
from app.services.seo.helpers import strip_html
from app.services.seo.human_presence_service import (
    _extract_paragraphs,
    _extract_sections,
    score_conclusion,
    score_human_markers,
    score_intro_quality,
    score_paragraph_variation,
    score_section_positions,
    score_vocabulary,
)

# ── Critère 2 — Densité informationnelle ────────────────────────────────

_FILLER_PATTERNS = (
    "il convient de noter que", "comme nous venons de le voir",
    "cela étant dit", "il va sans dire que", "il est donc",
)


def score_information_density(content: str) -> tuple[float, list[str]]:
    """Approxime la densité informationnelle en comptant les phrases de
    remplissage connues plutôt qu'en jugeant chaque phrase individuellement
    (jugement sémantique hors de portée d'une heuristique fiable) — un
    faux négatif ici est préférable à un faux positif qui pénaliserait à
    tort un article dense mais long."""
    text = strip_html(content).lower()
    hits = sum(1 for pattern in _FILLER_PATTERNS if pattern in text)
    flags = [f"phrase_remplissage:{p}" for p in _FILLER_PATTERNS if p in text]
    score = max(100.0 - hits * 20.0, 0.0)
    return score, flags


# ── Critère 6 — Dosage du "vous" ────────────────────────────────────────

def score_vous_dosage(content: str) -> tuple[float, list[str]]:
    paragraphs = _extract_paragraphs(content)
    flags = []
    max_consecutive = 0
    for p in paragraphs:
        sentences = [s.strip() for s in re.split(r"[.!?]+", p) if s.strip()]
        consecutive = 0
        for s in sentences:
            if re.match(r"^vous\b", s.lower()) or " vous devez" in s.lower():
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 0
    if max_consecutive >= 3:
        flags.append("saturation_vous")
        return 0.0, flags
    if max_consecutive == 2:
        flags.append("concentration_vous")
        return 60.0, flags
    return 100.0, flags


# ── Critère 7 — Connecteurs variés ──────────────────────────────────────
# Aligné sur les connecteurs que le prompt du writer encourage réellement :
# "pourtant", "à bien y réfléchir", "en réalité", "pour être honnête" sont
# désormais bannis (liste noire du prompt) et ne doivent plus être récompensés.

_VARIED_CONNECTORS = (
    "ce qui signifie concrètement", "tout compte tenu", "cela dit",
    "autrement dit", "tout compte fait", "paradoxalement", "curieusement",
    "malgré tout", "contrairement à", "et c'est là que ça devient intéressant",
)


def score_connector_variety(content: str) -> tuple[float, list[str]]:
    text = strip_html(content).lower()
    mais_count = len(re.findall(r"\bmais\b", text)) + len(re.findall(r"\bcependant\b", text))
    varied_count = sum(1 for c in _VARIED_CONNECTORS if c in text)
    flags = []
    if varied_count == 0 and mais_count > 0:
        flags.append("connecteurs_non_varies")
        return 0.0, flags
    if varied_count <= 1 and mais_count > 2:
        flags.append("mais_dominant")
        return 60.0, flags
    return 100.0, flags


# ── Critère 10 — Absence d'interdictions (réutilise check_style_compliance) ──

def score_forbidden_absence(content: str) -> tuple[float, list[str]]:
    style_check = check_style_compliance(content)
    blocking_issues = [
        i for i in style_check.get("issues", [])
        if i == "tiret_cadratin_present"
        or i.startswith("ouverture_generique:")
        or i.startswith("transition_creuse:")
        or i == "empilement_transitions"
    ]
    _, vocab_flags = score_vocabulary(content)
    superlative_flags = [f for f in vocab_flags if f.startswith("superlatif_vide:")]
    all_flags = blocking_issues + superlative_flags
    if all_flags:
        return 0.0, all_flags
    return 100.0, []


# ── Critère 8 — Moment de surprise (jugement LLM, pas d'heuristique fiable) ──

def score_surprise_moment(
    content: str, title: str = "", keyword: str = "", db=None, project_id: str | None = None,
) -> tuple[float | None, list[str]]:
    """Contrairement aux 9 autres critères, "une observation absente des 10
    premiers résultats Google" ne peut pas être vérifié par une regex — ça
    demande un jugement sur le fond. Délègue à agent_services.judge_surprise_
    moment (LLM) ; si le provider est indisponible, retourne None plutôt
    qu'un faux score, pour ne jamais donner une fausse impression de
    fiabilité sur ce point précis (les 10 points restent alors hors du
    total plutôt que comptés comme 0 — voir review_article)."""
    from app.services.agents.agent_services import judge_surprise_moment
    result = judge_surprise_moment(content, title, keyword, db=db, project_id=project_id)
    if result.get("status") != "success" or result.get("score") is None:
        return None, ["jugement_llm_indisponible"]
    flags = [] if result["score"] > 0 else [f"aucun_angle_original:{result.get('reasoning', '')[:80]}"]
    return result["score"], flags


_CRITERIA_WEIGHTS = {
    "introduction": 15,
    "densite_informationnelle": 15,
    "variation_paragraphes": 10,
    "position_tranchee": 15,
    "marqueurs_humains": 10,
    "dosage_vous": 5,
    "connecteurs": 5,
    "moment_surprise": 10,
    "conclusion": 10,
    "absence_interdictions": 5,
}
_BLOCKING_CRITERIA = {"introduction", "position_tranchee", "moment_surprise", "absence_interdictions"}


def review_article(
    content: str | None, word_count: int | None = None,
    *, title: str = "", keyword: str = "", db=None, project_id: str | None = None,
) -> dict:
    """Point d'entrée de l'agent réviseur — grille de scoring à 10 critères
    (100 points) + décision de publication, format aligné sur le rapport
    de révision demandé (docs/GUIDE-FORMATION-IA.md Partie 4).

    title/keyword/db/project_id sont optionnels et servent uniquement au
    critère "moment de surprise" (jugement LLM) — sans eux, ce critère
    reste non noté (10 points hors du total) plutôt que d'échouer."""
    if not content or len(strip_html(content).strip()) < 50:
        return {
            "status": "empty", "total_score": None, "decision": "REECRITURE",
            "criteria": {}, "blocking_triggered": ["no_content"],
        }

    wc = word_count or len(strip_html(content).split())

    intro_score, intro_flags = score_intro_quality(content, wc)
    density_score, density_flags = score_information_density(content)
    paragraph_score, paragraph_flags = score_paragraph_variation(content)
    position_score, position_flags = score_section_positions(content)
    marker_score, marker_flags = score_human_markers(content)
    vous_score, vous_flags = score_vous_dosage(content)
    connector_score, connector_flags = score_connector_variety(content)
    surprise_score, surprise_flags = score_surprise_moment(content, title, keyword, db=db, project_id=project_id)
    conclusion_score, conclusion_flags = score_conclusion(content, wc)
    forbidden_score, forbidden_flags = score_forbidden_absence(content)

    raw_scores = {
        "introduction": intro_score,
        "densite_informationnelle": density_score,
        "variation_paragraphes": paragraph_score,
        "position_tranchee": position_score,
        "marqueurs_humains": marker_score,
        "dosage_vous": vous_score,
        "connecteurs": connector_score,
        "moment_surprise": surprise_score,
        "conclusion": conclusion_score,
        "absence_interdictions": forbidden_score,
    }
    flags_by_criterion = {
        "introduction": intro_flags,
        "densite_informationnelle": density_flags,
        "variation_paragraphes": paragraph_flags,
        "position_tranchee": position_flags,
        "marqueurs_humains": marker_flags,
        "dosage_vous": vous_flags,
        "connecteurs": connector_flags,
        "moment_surprise": surprise_flags,
        "conclusion": conclusion_flags,
        "absence_interdictions": forbidden_flags,
    }

    criteria_detail = {}
    total_score = 0.0
    total_weight_scored = 0
    blocking_triggered = []

    for key, weight in _CRITERIA_WEIGHTS.items():
        raw = raw_scores[key]
        if raw is None:
            criteria_detail[key] = {
                "score": None, "max": weight, "flags": flags_by_criterion[key],
                "status": "jugement_requis",
            }
            continue
        points = round((raw / 100.0) * weight, 1)
        total_score += points
        total_weight_scored += weight
        is_zero_blocking = raw == 0.0 and key in _BLOCKING_CRITERIA
        criteria_detail[key] = {
            "score": points, "max": weight, "flags": flags_by_criterion[key],
            "status": "bloquant" if is_zero_blocking else "ok",
        }
        if is_zero_blocking:
            blocking_triggered.append(key)

    # Le score total reste sur 100 même si "moment_surprise" (10 pts) est
    # non noté (jugement requis) : ces 10 points sont simplement absents du
    # calcul plutôt que comptés comme 0, pour ne pas pénaliser injustement
    # un article dont ce seul critère n'a pas pu être vérifié automatiquement.
    if blocking_triggered:
        decision = "REECRITURE"
    elif total_score >= 75:
        decision = "APPROUVE"
    elif total_score >= 70:
        decision = "REVISION_AUTOMATIQUE"
    else:
        decision = "REECRITURE"

    return {
        "status": "reviewed",
        "total_score": round(total_score, 1),
        "total_weight_scored": total_weight_scored,
        "decision": decision,
        "criteria": criteria_detail,
        "blocking_triggered": blocking_triggered,
        "note": (
            "moment_surprise (10 pts) nécessite un jugement humain ou LLM, non inclus "
            "dans le calcul automatique — voir agent_services.check_reader_retention "
            "pour une évaluation LLM équivalente si souhaitée."
        ),
    }
