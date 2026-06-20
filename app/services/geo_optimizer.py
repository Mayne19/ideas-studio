from __future__ import annotations

import re
from typing import Any


def analyze_geo_readiness(
    content: str | None,
    title: str | None = None,
    keyword: str | None = None,
    faq_json: str | None = None,
    sources_json: dict | None = None,
) -> dict[str, Any]:
    """Analyze article for GEO (Generative Engine Optimization) readiness.

    Checks:
    - direct_answer: main answer appears early
    - definition_present: clear definition if complex topic
    - autonomous_sections: sections are self-contained
    - citable_sentences: concise, quotable sentences
    - lists_tables: structured data formats
    - named_entities: people, places, brands mentioned
    - sources_present: external references
    - faq_present: FAQ available
    - no_ambiguity: clear, unambiguous language
    """
    text = content or ""
    text_clean = re.sub(r"<[^>]+>", " ", text) if text else ""
    text_clean = re.sub(r"\s+", " ", text_clean).strip()

    checks: list[dict[str, Any]] = []
    score = 0.0
    max_score = 0.0

    def _check(key: str, label: str, passed: bool, comment: str) -> None:
        checks.append({"key": key, "label": label, "passed": passed, "comment": comment})

    # 1. Direct answer in first paragraph
    max_score += 15
    first_para = ""
    if text_clean:
        paras = re.split(r"\n\s*\n", text_clean)
        if paras:
            first_para = paras[0].strip()
    first_120 = first_para[:120] if first_para else (title or "")[:120]

    has_direct_answer = bool(first_120) and len(first_120) > 30
    _check(
        "direct_answer", "Réponse directe dès le début",
        has_direct_answer,
        "La réponse principale apparaît dans l'introduction." if has_direct_answer
        else "L'introduction ne contient pas de réponse directe satisfaisante.",
    )
    if has_direct_answer:
        score += 15

    # 2. Citable sentences (concise, < 25 words)
    max_score += 15
    sentences = re.split(r"[.!?]+", text_clean) if text_clean else []
    citable = [s.strip() for s in sentences if 8 < len(s.split()) < 25]
    has_citable = len(citable) >= 3
    _check(
        "citable_sentences", "Phrases citables",
        has_citable,
        f"{len(citable)} phrases synthétiques et citables détectées." if has_citable
        else "Peu de phrases courtes et percutantes.",
    )
    if has_citable:
        score += 15

    # 3. Lists or tables
    max_score += 10
    has_lists = bool(re.search(r"<ul>|<ol>|<table>", text)) if text else False
    _check(
        "lists_tables", "Listes ou tableaux",
        has_lists,
        "Listes ou tableaux présents." if has_lists else "Pas de liste ou tableau détecté.",
    )
    if has_lists:
        score += 10

    # 4. Named entities
    max_score += 10
    entity_patterns = r"\b(?:France|Europe|Google|OpenAI|Microsoft|Apple|Amazon|Meta|Paris|Londres|New York|iOS|Android|Windows|ChatGPT|Gemini|Claude|Mistral)\b"
    entities = set(re.findall(entity_patterns, text_clean)) if text_clean else set()
    has_entities = len(entities) >= 2
    _check(
        "named_entities", "Entités nommées",
        has_entities,
        f"{len(entities)} entités nommées détectées." if has_entities
        else "Peu d'entités nommées identifiables.",
    )
    if has_entities:
        score += 10

    # 5. Sources present
    max_score += 10
    has_sources = bool(sources_json) or (text_clean and bool(re.search(r"selon|source|étude|rapport|d'après|cite", text_clean, re.IGNORECASE)))
    _check(
        "sources_present", "Sources présentes",
        has_sources,
        "Sources ou références détectées." if has_sources else "Aucune source explicite.",
    )
    if has_sources:
        score += 10

    # 6. FAQ present and useful
    max_score += 15
    faq_available = bool(faq_json)
    _check(
        "faq_present", "FAQ présente",
        faq_available,
        "FAQ disponible pour réponses génératives." if faq_available else "FAQ absente.",
    )
    if faq_available:
        score += 15

    # 7. Autonomous sections (H2 count >= 3)
    max_score += 10
    h2_count = len(re.findall(r"<h2[^>]*>", text)) if text else 0
    has_autonomous = h2_count >= 3
    _check(
        "autonomous_sections", "Sections autonomes",
        has_autonomous,
        f"{h2_count} sections H2 détectées." if has_autonomous
        else f"Seulement {h2_count} section(s) H2 — privilégier des sections autonomes.",
    )
    if has_autonomous:
        score += 10

    # 8. No ambiguity
    max_score += 8
    ambiguous_terms = re.findall(r"\b(?:peut-être|peut être|possiblement|probablement|on pourrait)\b", text_clean, re.IGNORECASE) if text_clean else []
    has_no_ambiguity = len(ambiguous_terms) <= 3
    _check(
        "no_ambiguity", "Absence d'ambiguïté",
        has_no_ambiguity,
        f"{len(ambiguous_terms)} terme(s) ambigu(s) détecté(s)." if not has_no_ambiguity
        else "Langage clair et direct.",
    )
    if has_no_ambiguity:
        score += 8

    # 9. Keyword in title
    max_score += 7
    kw_in_title = bool(keyword and title and keyword.lower() in title.lower())
    _check(
        "keyword_in_title", "Mot-clé dans le titre",
        kw_in_title,
        "Le mot-clé principal figure dans le titre." if kw_in_title else "Le mot-clé principal est absent du titre.",
    )
    if kw_in_title:
        score += 7

    geo_score = round((score / max_score) * 100) if max_score > 0 else 0

    recommendations: list[str] = []
    for c in checks:
        if not c["passed"]:
            recommendations.append(c["comment"])

    if geo_score >= 80:
        status = "good"
    elif geo_score >= 50:
        status = "needs_improvement"
    else:
        status = "weak"

    return {
        "geo_score": geo_score,
        "status": status,
        "checks": checks,
        "recommendations": recommendations,
        "max_score": max_score,
        "score": score,
    }
