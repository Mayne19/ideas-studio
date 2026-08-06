from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from app.services.seo.format_expectations import FormatExpectations, get_expectations, get_format, normalize_to_format
from app.services.seo.helpers import strip_html


GENERIC_AI_PATTERNS = [
    "dans cet article, nous allons voir",
    "il est important de noter que",
    "en conclusion, nous pouvons dire",
    "comme nous l'avons vu précédemment",
    "pour résumer ce que nous venons de voir",
    "il convient tout d'abord de définir",
    "dans un premier temps, puis dans un second temps",
    "cet article a pour objectif de",
    "nous espérons que cet article vous a aidé",
    "n'hésitez pas à partager cet article",
    "bienvenue dans cet article",
    "dans ce guide complet",
    "tout ce que vous devez savoir",
]

CONCRETE_EXAMPLE_INTROS = [
    "par exemple", "prenons le cas de", "imaginons que",
    "prenons l'exemple de", "à titre d'exemple", "concrètement",
    "illustrons avec", "supposons que",
]


def _ngrams(text: str, n: int = 3) -> set[str]:
    words = re.findall(r"\b\w+\b", text.lower())
    return {" ".join(words[i: i + n]) for i in range(len(words) - n + 1)}


def _cosine_similarity_ngram(text_a: str, text_b: str, n: int = 3) -> float:
    a = Counter(_ngrams(text_a, n))
    b = Counter(_ngrams(text_b, n))
    if not a or not b:
        return 0.0
    dot = sum(a[k] * b[k] for k in a if k in b)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _fingerprint(article: Any) -> str:
    if isinstance(article, dict):
        title = article.get("title") or ""
        content = article.get("content") or ""
    else:
        title = getattr(article, "title", "") or ""
        content = getattr(article, "content", "") or ""
    text = strip_html(content)
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    first_five = " ".join(sentences[:5])
    return f"{title} {first_five}"


def score_ai_generic_absence(text: str) -> float:
    hits = sum(1 for p in GENERIC_AI_PATTERNS if p in text.lower())
    return max(0.0, 100.0 - hits * 15)


def score_internal_uniqueness(article: Any, project_articles: list[Any]) -> float:
    if not project_articles:
        return 75.0
    fp = _fingerprint(article)
    article_id = article.get("id") if isinstance(article, dict) else getattr(article, "id", None)
    similarities = []
    for a in project_articles:
        a_id = a.get("id") if isinstance(a, dict) else getattr(a, "id", None)
        if a_id == article_id:
            continue
        sim = _cosine_similarity_ngram(fp, _fingerprint(a))
        similarities.append(sim)
    if not similarities:
        return 75.0
    max_sim = max(similarities)
    if max_sim < 0.15:  return 100.0
    if max_sim < 0.30:  return 80.0
    if max_sim < 0.45:  return 55.0
    if max_sim < 0.60:  return 30.0
    return 0.0


def score_source_verification(text: str, sources: list[str]) -> tuple[float, str]:
    if not sources:
        return 50.0, "unverified"

    similarities = [_cosine_similarity_ngram(text, s) for s in sources if s]
    if not similarities:
        return 50.0, "unverified"

    max_sim = max(similarities)
    if max_sim > 0.55:  return 40.0, "high_overlap"
    if max_sim > 0.30:  return 70.0, "acceptable"
    if max_sim > 0.10:  return 90.0, "original"
    return 100.0, "adds_value"


def score_competitor_similarity(content: str, competitor_texts: list[str]) -> tuple[float, list[str]]:
    """Détecte les passages proches du contenu concurrent (SERP/scraping) au
    niveau phrase — une similarité n-gram calculée sur l'article entier se
    dilue et laisse passer un paragraphe recopié d'un concurrent. On compare
    chaque phrase de l'article aux textes concurrents : si ≥60% des trigrammes
    d'une phrase existent déjà chez un concurrent, c'est un signal fort de
    paraphrase trop proche. 100% heuristique, aucun appel LLM."""
    if not competitor_texts:
        return 100.0, []
    sentences = [s.strip() for s in re.split(r"[.!?]+", strip_html(content)) if len(s.strip()) >= 20]
    if not sentences:
        return 100.0, []
    competitor_ngrams = _ngrams(" ".join(competitor_texts), 3)
    if not competitor_ngrams:
        return 100.0, []
    flagged: list[str] = []
    for sentence in sentences:
        ngrams = _ngrams(sentence, 3)
        if not ngrams:
            continue
        overlap = len(ngrams & competitor_ngrams) / len(ngrams)
        if overlap >= 0.60:
            flagged.append(sentence[:90])
    if not flagged:
        return 100.0, []
    score = max(0.0, 100.0 - len(flagged) * 15.0)
    return score, [f"passage_concurrent:{passage}" for passage in flagged[:5]]


def _count_concrete_examples(text: str) -> int:
    count = 0
    text_lower = text.lower()
    for intro in CONCRETE_EXAMPLE_INTROS:
        idx = 0
        while True:
            pos = text_lower.find(intro, idx)
            if pos == -1:
                break
            window = text[pos: pos + 150]
            has_specific = bool(
                re.search(r"[A-Z][a-zA-Z]+", window) or
                re.search(r"\d", window) or
                re.search(r"\b(france|paris|europe|google|amazon|apple)\b", window, re.IGNORECASE)
            )
            if has_specific:
                count += 1
            idx = pos + 1
    return count


def score_own_examples(text: str, fmt: FormatExpectations) -> float:
    count = _count_concrete_examples(text)
    return normalize_to_format(count, fmt.min_examples, fmt.ideal_examples)


def compute_originality_score(article: Any, project_articles: list[Any] | None = None) -> dict:
    if isinstance(article, dict):
        content = article.get("content") or ""
        sources_json = article.get("extracted_sources_json") or article.get("sources_json") or {}
    else:
        content = getattr(article, "content", None) or ""
        sources_json = getattr(article, "extracted_sources_json", None) or getattr(article, "sources_json", None) or {}

    fmt_obj = get_expectations(article)
    fmt = get_format(article)

    text = strip_html(content)
    word_count = len(text.split())

    if not content or len(content.strip()) < 50 or word_count < 500:
        return {
            "score": 50,
            "confidence": "low",
            "method": "rules",
            "content_format": fmt,
            "status": "unverified",
            "signals": {},
            "flags": ["insufficient_content"] if word_count < 500 else ["no_content"],
            "explanation": (
                f"Contenu insuffisant pour évaluer l'originalité ({word_count} mots — "
                "500 mots minimum requis pour une vérification fiable)."
                if word_count < 500
                else "Contenu insuffisant pour évaluer l'originalité."
            ),
            "version": "2.2",
        }

    sources: list[str] = []
    if isinstance(sources_json, dict):
        for v in sources_json.values():
            if isinstance(v, str):
                sources.append(v)
            elif isinstance(v, list):
                sources.extend(str(x) for x in v)
    elif isinstance(sources_json, list):
        sources = [str(x) for x in sources_json]

    s1 = score_ai_generic_absence(text)
    s2 = score_internal_uniqueness(article, project_articles or [])
    s3_score, s3_status = score_source_verification(text, sources)
    s4 = score_own_examples(text, fmt_obj)
    # Similarité phrase à phrase contre le contenu concurrent (les snippets
    # SERP du research brief sont de vraies pages concurrentes) : complète
    # score_source_verification, diluée sur l'article entier.
    s5, s5_flags = score_competitor_similarity(content, sources)

    rules_score = s1 * 0.30 + s2 * 0.20 + s3_score * 0.15 + s4 * 0.10 + s5 * 0.25
    final_score = round(rules_score)

    if s3_status == "unverified":
        final_score = min(final_score, 65)

    flags: list[str] = []
    if s3_status == "unverified":
        flags.append("no_sources_unverified")
    if s3_status == "high_overlap":
        flags.append("high_source_overlap")
    if s1 < 70:
        flags.append("generic_ai_patterns_detected")
    if s2 == 0:
        flags.append("probable_internal_duplicate")
    if s5 < 70:
        flags.append("competitor_similarity_high")
    flags.extend(s5_flags)

    available = sum(1 for v in [s1, s2, s3_score, s4, s5] if v is not None)
    confidence = "high" if available >= 4 else "medium"
    if s3_status == "unverified":
        confidence = "medium"

    signals = {
        "ai_generic_absence": {"value": round(s1), "weight": 0.30, "contribution": round(s1 * 0.30, 1)},
        "internal_uniqueness": {"value": round(s2), "weight": 0.20, "contribution": round(s2 * 0.20, 1)},
        "source_verification": {"value": round(s3_score), "weight": 0.15, "contribution": round(s3_score * 0.15, 1), "status": s3_status},
        "concrete_examples":   {"value": round(s4), "weight": 0.10, "contribution": round(s4 * 0.10, 1)},
        "competitor_similarity": {"value": round(s5), "weight": 0.25, "contribution": round(s5 * 0.25, 1)},
    }

    explanation_parts = []
    if s1 < 70:
        explanation_parts.append("phrases génériques IA détectées")
    if s2 == 0:
        explanation_parts.append("doublon interne probable")
    if s3_status == "unverified":
        explanation_parts.append("originalité non vérifiée — aucune source fournie")
    elif s3_status == "high_overlap":
        explanation_parts.append("fort chevauchement avec les sources")
    if s5 < 70:
        explanation_parts.append("passages trop proches du contenu concurrent")
    if not explanation_parts:
        explanation_parts.append("contenu original, aucun signal négatif majeur")

    return {
        "score": final_score,
        "confidence": confidence,
        "method": "rules",
        "content_format": fmt,
        "status": s3_status,
        "signals": signals,
        "flags": flags,
        "explanation": f"Originalité {fmt} : " + "; ".join(explanation_parts) + ".",
        "version": "2.2",
    }


def check_originality_dict(
    content: str | None, sources: list[str] | None = None,
    project_articles: list[dict] | None = None, title: str | None = None,
) -> dict:
    """Wrapper appelé par l'orchestrateur. `project_articles` (optionnel) alimente
    score_internal_uniqueness() — sans lui, ce signal (25% du score Originalité)
    retombait systématiquement sur son repli neutre 75/100 (voir
    score_internal_uniqueness: `if not project_articles: return 75.0`), incapable
    de détecter un vrai doublon interne, quel que soit le contenu réel. `title`
    alimente aussi l'empreinte comparée (_fingerprint) — sans lui, l'article
    courant se comparait avec un titre vide face aux vrais titres des autres."""
    article = {"content": content or "", "sources_json": sources or [], "title": title or ""}
    result = compute_originality_score(article, project_articles or [])
    return {
        "heuristic_score": result["score"],
        "method": "heuristic",
        "real_plagiarism_tool_used": False,
        "risk_level": "low" if result["score"] >= 70 else "medium",
        "manual_review_needed": result["status"] == "unverified",
        "suspicious_passages": [],
        "compared_sources": [],
        "v2": result,
    }
