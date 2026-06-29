from __future__ import annotations

import re
from typing import Any

from app.services.seo.format_expectations import get_format
from app.services.seo.helpers import strip_html


QUESTION_WORDS = ["comment", "pourquoi", "qu'est-ce", "quand", "où", "qui", "quels", "quelle", "combien"]
ACTION_VERBS = ["permet", "aide", "améliore", "réduit", "augmente", "garantit", "évite", "explique"]

SUMMARY_MARKERS = [
    "en résumé", "tl;dr", "à retenir", "points clés", "l'essentiel",
    "pour résumer", "en bref", "synthèse", "conclusion rapide",
]

SCHEMA_POINTS: dict[str, int] = {
    "FAQPage": 40,
    "HowTo": 35,
    "Article": 25,
    "BlogPosting": 25,
    "BreadcrumbList": 10,
    "Organization": 15,
    "Author": 15,
    "Person": 15,
}

ENTITY_PATTERNS = [
    re.compile(r"\b[A-Z][a-zA-Z]+(?: [A-Z][a-zA-Z]+){0,2}\b"),
    re.compile(r"\b\d{4}\b"),
    re.compile(r"\b\d+[\.,]\d+\s*(?:€|\$|%|km|kg|millions?)\b", re.IGNORECASE),
]


def _extract_headings_h2(html_content: str) -> list[str]:
    h2 = re.findall(r"<h2[^>]*>(.*?)</h2>", html_content, re.IGNORECASE | re.DOTALL)
    return [strip_html(h).strip() for h in h2 if strip_html(h).strip()]


def _extract_sections_after_h2(html_content: str) -> list[str]:
    parts = re.split(r"<h2[^>]*>.*?</h2>", html_content, flags=re.IGNORECASE | re.DOTALL)
    return [strip_html(p).strip() for p in parts[1:] if strip_html(p).strip()]


def _get_first_sentence(text: str) -> str:
    sentences = re.split(r"[.!?]+", text)
    for s in sentences:
        s = s.strip()
        if s:
            return s
    return ""


def _is_self_contained_answer(sentence: str) -> bool:
    words = sentence.split()
    if len(words) < 8:
        return False
    if sentence.strip().endswith("?"):
        return False
    if re.match(r"^(il|elle|ils|elles|ce|cela|ça|qui|que|dont)\b", sentence.lower()):
        return False
    if re.search(r"\b(est|sont|permet|aide|implique|signifie|correspond|désigne)\b", sentence.lower()):
        return True
    if len(words) >= 12:
        return True
    return False


def _extract_named_entities(text: str) -> list[str]:
    entities = set()
    for pattern in ENTITY_PATTERNS:
        for match in pattern.findall(text):
            if isinstance(match, str) and len(match) >= 2:
                entities.add(match)
    return list(entities)


def score_direct_answers(html_content: str) -> float:
    sections = _extract_sections_after_h2(html_content)
    if not sections:
        return 30.0
    direct_count = sum(
        1 for section in sections
        if _is_self_contained_answer(_get_first_sentence(section))
    )
    return round((direct_count / len(sections)) * 100)


def score_heading_format(headings: list[str]) -> float:
    if not headings:
        return 30.0
    score = sum(
        1.0 if any(q in h.lower() for q in QUESTION_WORDS)
        else 0.5 if any(v in h.lower() for v in ACTION_VERBS)
        else 0.0
        for h in headings
    )
    ratio = score / len(headings)
    if ratio < 0.20:  return 20.0
    if ratio < 0.40:  return 50.0
    if ratio < 0.60:  return 75.0
    return 95.0


def score_structured_data(metadata: Any) -> float:
    if isinstance(metadata, dict):
        schema = metadata.get("structured_data_json") or metadata.get("json_ld") or []
    else:
        raw = getattr(metadata, "structured_data_json", None)
        schema = raw if isinstance(raw, list) else []

    if not schema:
        return 0.0

    total = sum(SCHEMA_POINTS.get(e.get("@type", "") if isinstance(e, dict) else "", 0) for e in schema)
    return min(100.0, float(total))


def score_named_entities(text: str, word_count: int) -> float:
    entities = _extract_named_entities(text)
    density = (len(entities) / max(word_count, 1)) * 1000
    if density < 2:   return 20.0
    if density < 5:   return 55.0
    if density < 10:  return 80.0
    return 100.0


def score_summaries(text: str) -> float:
    found = sum(1 for m in SUMMARY_MARKERS if m in text.lower())
    if found == 0:   return 10.0
    if found == 1:   return 60.0
    if found == 2:   return 85.0
    return 100.0


def score_semantic_density(text: str, target_keyword: str | None, related_terms: list[str] | None = None) -> float:
    if not target_keyword:
        return 50.0
    text_lower = text.lower()
    if not related_terms:
        words = set(re.findall(r"\b[a-zA-ZÀ-ÿ]{4,}\b", target_keyword.lower()))
        related_terms = list(words) if words else []
    if not related_terms:
        return 50.0
    covered = sum(1 for t in related_terms if t.lower() in text_lower)
    return round((covered / max(len(related_terms), 1)) * 100)


def compute_geo_score(article: Any) -> dict:
    if isinstance(article, dict):
        content = article.get("content") or ""
        keyword = article.get("keyword") or ""
    else:
        content = getattr(article, "content", None) or ""
        keyword = getattr(article, "keyword", None) or ""

    fmt = get_format(article)

    if not content or len(content.strip()) < 50:
        return {
            "score": 0,
            "confidence": "low",
            "method": "rules",
            "content_format": fmt,
            "signals": {},
            "flags": ["no_content"],
            "explanation": "Contenu insuffisant pour évaluer le GEO.",
            "version": "2.1",
        }

    text = strip_html(content)
    word_count = len(text.split())
    headings_h2 = _extract_headings_h2(content)

    s1 = score_direct_answers(content)
    s2 = score_heading_format(headings_h2)
    s3 = score_structured_data(article)
    s4 = score_named_entities(text, word_count)
    s5 = score_summaries(text)
    s6 = score_semantic_density(text, keyword)

    final_score = round(
        s1 * 0.25
        + s2 * 0.20
        + s3 * 0.20
        + s4 * 0.15
        + s5 * 0.10
        + s6 * 0.10
    )

    flags: list[str] = []
    if s3 == 0:
        flags.append("no_structured_data")
    if s5 <= 10:
        flags.append("no_summary_block")
    if s1 < 40:
        flags.append("sections_lack_direct_answers")

    signals = {
        "direct_answers":    {"value": round(s1), "weight": 0.25, "contribution": round(s1 * 0.25, 1)},
        "heading_format":    {"value": round(s2), "weight": 0.20, "contribution": round(s2 * 0.20, 1)},
        "structured_data":   {"value": round(s3), "weight": 0.20, "contribution": round(s3 * 0.20, 1)},
        "named_entities":    {"value": round(s4), "weight": 0.15, "contribution": round(s4 * 0.15, 1)},
        "summary_blocks":    {"value": round(s5), "weight": 0.10, "contribution": round(s5 * 0.10, 1)},
        "semantic_density":  {"value": round(s6), "weight": 0.10, "contribution": round(s6 * 0.10, 1)},
    }

    available = sum(1 for v in [s1, s2, s4, s5, s6] if v is not None)
    confidence = "high" if available >= 4 else "medium"

    strengths = [k for k, v in signals.items() if v["value"] >= 75]
    weaknesses = [k for k, v in signals.items() if v["value"] < 40]
    explanation = (
        f"GEO {fmt} : score {final_score}/100. "
        + (f"Points forts : {', '.join(strengths)}. " if strengths else "")
        + (f"À améliorer : {', '.join(weaknesses)}." if weaknesses else "Aucune faiblesse majeure.")
    )

    return {
        "score": final_score,
        "confidence": confidence,
        "method": "rules",
        "content_format": fmt,
        "signals": signals,
        "flags": flags,
        "explanation": explanation,
        "geo_score": final_score,
        "version": "2.1",
    }
