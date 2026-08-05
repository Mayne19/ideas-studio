from __future__ import annotations

import re
from statistics import mean
from typing import Any

from app.services.seo.helpers import strip_html


TRANSITION_WORDS = [
    # "de plus"/"en outre"/"par ailleurs"/"toutefois"/"néanmoins" et
    # "en conclusion"/"pour conclure"/"en résumé" volontairement absents :
    # le prompt du rédacteur (seo_generation_orchestrator._generate_content,
    # règles de voix + vocabulaire interdit) les bannit explicitement comme
    # "transitions creuses" ou ouvertures de conclusion interdites — les
    # récompenser ici contredisait directement la consigne donnée au writer.
    "donc", "ainsi", "par conséquent", "c'est pourquoi", "de ce fait",
    "également", "cependant", "en revanche", "pourtant",
    "à bien y réfléchir", "ce qui signifie concrètement", "tout compte fait",
    "en réalité", "pour être honnête", "paradoxalement", "curieusement",
    "malgré tout", "autrement dit",
    "par exemple", "notamment", "ainsi que", "finalement",
]

PASSIVE_PATTERNS = [
    r"\best\s+\w+é[es]?\b",
    r"\bsont\s+\w+é[es]?\b",
    r"\bétait\s+\w+é[es]?\b",
    r"\bétaient\s+\w+é[es]?\b",
    r"\bfut\s+\w+é[es]?\b",
    r"\bse\s+trouve(?:nt)?\s+\w+é[es]?\b",
]


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip() and len(s.split()) >= 3]


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"\b[a-zA-ZÀ-ÿ]+\b", text)


def _count_words(text: str) -> int:
    return len(_tokenize_words(text))


def _extract_paragraphs(html_content: str) -> list[str]:
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html_content, flags=re.IGNORECASE | re.DOTALL)
    if paragraphs:
        return [strip_html(p).strip() for p in paragraphs if strip_html(p).strip()]
    return [p.strip() for p in html_content.split("\n\n") if p.strip()]


def _is_passive_sentence(sentence: str) -> bool:
    for pattern in PASSIVE_PATTERNS:
        if re.search(pattern, sentence, flags=re.IGNORECASE):
            return True
    return False


def compute_lix(text: str) -> float:
    sentences = _split_sentences(text)
    words = _tokenize_words(text)

    if not sentences or not words:
        return 40.0

    L = len(words)
    Ph = len(sentences)
    Mo = sum(1 for w in words if len(w) > 6)

    return (L / Ph) + ((Mo * 100) / L)


def lix_to_score(lix: float) -> float:
    if lix <= 20: return 95
    if lix <= 30: return 85
    if lix <= 40: return 75
    if lix <= 50: return 60
    if lix <= 60: return 40
    if lix <= 70: return 20
    return 5


def score_paragraph_length(html_content: str) -> float:
    """Barème aligné sur la règle absolue du prompt du rédacteur : paragraphes
    de 1 à 4 phrases (cible 2-3), soit ~10-60 mots en français courant. Avant
    ce fix, la fourchette 40-100 mots (plutôt 4-6 phrases) était notée au
    maximum tandis que la cible réelle du writer (2-3 phrases courtes,
    ~10-60 mots) plafonnait à 65/100 — le score pénalisait la structure
    même que le writer est explicitement instruit de produire."""
    paragraphs = _extract_paragraphs(html_content)
    if not paragraphs:
        return 50.0
    avg = mean(_count_words(p) for p in paragraphs)
    if avg < 10:       return 70.0
    if avg <= 60:      return 100.0
    if avg <= 90:      return 75.0
    if avg <= 130:     return 50.0
    return 20.0


def score_active_voice(text: str) -> float:
    sentences = _split_sentences(text)
    if not sentences:
        return 75.0
    passive_ratio = sum(1 for s in sentences if _is_passive_sentence(s)) / len(sentences)
    if passive_ratio < 0.05:  return 100.0
    if passive_ratio < 0.15:  return 85.0
    if passive_ratio < 0.25:  return 65.0
    if passive_ratio < 0.40:  return 40.0
    return 15.0


def score_transitions(text: str, word_count: int) -> float:
    found = sum(1 for t in TRANSITION_WORDS if t in text.lower())
    density = (found / max(word_count, 1)) * 1000
    if density < 1.0:   return 30.0
    if density < 2.0:   return 60.0
    if density < 4.0:   return 88.0
    if density < 6.0:   return 100.0
    return 75.0  # oversaturation = artificial


def compute_readability_score(article: Any) -> dict:
    if isinstance(article, dict):
        content = article.get("content") or ""
    else:
        content = getattr(article, "content", None) or ""

    if not content or len(content.strip()) < 50:
        return {
            "score": None,
            "confidence": "low",
            "method": "rules",
            "signals": {},
            "flags": ["no_content"],
            "explanation": "Contenu insuffisant pour évaluer la lisibilité.",
            "version": "2.1",
        }

    text = strip_html(content)
    word_count = _count_words(text)

    lix = compute_lix(text)
    lix_score = lix_to_score(lix)
    para_score = score_paragraph_length(content)
    passive_score = score_active_voice(text)
    transition_score = score_transitions(text, word_count)

    final_score = (
        lix_score * 0.60
        + para_score * 0.20
        + passive_score * 0.10
        + transition_score * 0.10
    )

    flags = []
    if lix > 55:
        flags.append("high_lix_difficult_reading")
    if para_score < 50:
        flags.append("paragraph_length_issue")

    signals = {
        "lix_score":       {"value": round(lix_score), "weight": 0.60, "contribution": round(lix_score * 0.60, 1), "lix": round(lix, 1)},
        "paragraph_score": {"value": round(para_score), "weight": 0.20, "contribution": round(para_score * 0.20, 1)},
        "passive_score":   {"value": round(passive_score), "weight": 0.10, "contribution": round(passive_score * 0.10, 1)},
        "transition_score":{"value": round(transition_score), "weight": 0.10, "contribution": round(transition_score * 0.10, 1)},
    }

    if lix <= 30:
        reading_label = "facile"
    elif lix <= 45:
        reading_label = "accessible"
    elif lix <= 55:
        reading_label = "moyen"
    else:
        reading_label = "difficile"

    explanation = (
        f"Lisibilité {reading_label} (LIX {round(lix, 1)}). "
        f"Paragraphes : {round(para_score)}/100. "
        + (f"Problèmes : {', '.join(flags)}." if flags else "Aucun problème détecté.")
    )

    available = sum(1 for v in [lix_score, para_score, passive_score, transition_score] if v is not None)
    confidence = "high" if available >= 3 else "medium"

    return {
        "score": round(final_score),
        "confidence": confidence,
        "method": "rules",
        "signals": signals,
        "flags": flags,
        "explanation": explanation,
        "version": "2.1",
    }
