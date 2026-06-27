from __future__ import annotations

import re
from itertools import combinations
from statistics import mean
from typing import Any

from app.services.seo.format_expectations import FormatExpectations, get_expectations, get_format, normalize_to_format
from app.services.seo.helpers import strip_html


NUANCE_MARKERS = [
    "cependant", "toutefois", "néanmoins", "en revanche",
    "d'un côté", "d'un autre côté", "il convient de nuancer",
    "selon les cas", "cela dépend", "dans certaines situations",
    "il faut distinguer", "en réalité", "contrairement à",
    "à condition que", "bien que", "même si", "quoique",
]

CITED_STAT_PATTERNS = [
    re.compile(r"\d+[\.,]?\d*\s*%[^.]{0,80}?(selon|source|d'après|d'apres|étude|rapport|insee)", re.IGNORECASE),
    re.compile(r"\d+[\.,]?\d*\s*(millions?|milliards?|milliers?)[^.]{0,80}?(selon|source|d'après|d'apres)", re.IGNORECASE),
]


def _extract_links(html_content: str) -> list[str]:
    return re.findall(r'href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)


def _is_internal(url: str, project_domain: str) -> bool:
    if url.startswith("#") or url.startswith("/"):
        return True
    if project_domain and project_domain in url:
        return True
    return False


def _extract_headings(html_content: str) -> tuple[list[str], list[str], list[str]]:
    h2 = re.findall(r"<h2[^>]*>(.*?)</h2>", html_content, re.IGNORECASE | re.DOTALL)
    h3 = re.findall(r"<h3[^>]*>(.*?)</h3>", html_content, re.IGNORECASE | re.DOTALL)
    all_h = h2 + h3
    clean_h2 = [strip_html(h).strip() for h in h2]
    clean_h3 = [strip_html(h).strip() for h in h3]
    clean_all = clean_h2 + clean_h3
    return clean_h2, clean_h3, clean_all


def _detect_faq(html_content: str, metadata: dict) -> bool:
    faq_lower = html_content.lower()
    if "<details" in faq_lower:
        return True
    if re.search(r'(faq|questions?\s+(fr[eé]quentes?|courantes?))', faq_lower):
        return True
    if metadata.get("faq_json"):
        return True
    if '"@type": "FAQPage"' in html_content or '"FAQPage"' in html_content:
        return True
    return False


def score_external_links(html_content: str, project_domain: str, fmt: FormatExpectations) -> float:
    links = _extract_links(html_content)
    external = [l for l in links if not _is_internal(l, project_domain) and l.startswith("http")]
    wikipedia = sum(1 for l in external if "wikipedia.org" in l)
    other = len(external) - wikipedia
    effective = other + (wikipedia * 0.5)
    return normalize_to_format(effective, fmt.min_external_links, fmt.ideal_external_links)


def score_cited_stats(text: str, fmt: FormatExpectations) -> float:
    cited = sum(1 for pattern in CITED_STAT_PATTERNS if pattern.search(text))
    return normalize_to_format(cited, fmt.min_cited_stats, fmt.ideal_cited_stats)


def score_heading_structure(h2: list[str], h3: list[str], fmt: FormatExpectations) -> float:
    h2_score = normalize_to_format(len(h2), fmt.min_h2_count, fmt.ideal_h2_count)
    if len(h2) >= 2:
        ratio = len(h3) / len(h2)
        h3_score = min(100.0, ratio * 50)
    else:
        h3_score = 75.0
    return h2_score * 0.60 + h3_score * 0.40


def score_faq(html_content: str, metadata: dict, fmt: FormatExpectations) -> float:
    has_faq = _detect_faq(html_content, metadata)
    if not fmt.faq_required:
        return 100.0 if has_faq else 65.0
    return 100.0 if has_faq else 20.0


def score_author_bio(author_bio: str | None, author_url: str | None) -> float:
    if not author_bio:
        return 0.0
    bio = author_bio.strip()
    if len(bio) < 50:
        return 30.0
    if len(bio) >= 150 and author_url:
        return 100.0
    if len(bio) >= 50:
        return 70.0
    return 30.0


def score_nuance_markers(text: str, word_count: int) -> float:
    found = {m for m in NUANCE_MARKERS if m in text.lower()}
    density = (len(found) / max(word_count, 1)) * 1000
    if density == 0:     return 0.0
    if density < 0.5:    return 30.0
    if density < 1.0:    return 60.0
    if density < 2.0:    return 80.0
    return 100.0


def _tokenize(heading: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-ZÀ-ÿ]{4,}", heading)}


def score_heading_diversity(headings: list[str]) -> float:
    if len(headings) < 2:
        return 65.0
    tokenized = [_tokenize(h) for h in headings if h]
    if len(tokenized) < 2:
        return 65.0
    similarities = [
        len(a & b) / len(a | b)
        for a, b in combinations(tokenized, 2)
        if a | b
    ]
    if not similarities:
        return 65.0
    avg_similarity = mean(similarities)
    return max(0.0, round(100 - avg_similarity * 150))


def compute_eeat_score(article: Any, project_domain: str = "") -> dict:
    if isinstance(article, dict):
        content = article.get("content") or ""
        metadata = article
        author_bio = article.get("author_bio")
        author_url = article.get("author_url")
    else:
        content = getattr(article, "content", None) or ""
        metadata = {
            "faq_json": getattr(article, "faq_json", None),
        }
        author_bio = getattr(article, "author_bio", None)
        author_url = getattr(article, "author_url", None)

    fmt_obj = get_expectations(article)
    fmt = get_format(article)

    if not content or len(content.strip()) < 50:
        return {
            "score": 0,
            "confidence": "low",
            "method": "rules",
            "content_format": fmt,
            "signals": {},
            "flags": ["no_content"],
            "explanation": "Contenu insuffisant pour évaluer l'EEAT.",
            "version": "2.1",
        }

    text = strip_html(content)
    word_count = len(text.split())
    h2, h3, all_headings = _extract_headings(content)

    s1 = score_external_links(content, project_domain, fmt_obj)
    s2 = score_cited_stats(text, fmt_obj)
    s3 = score_heading_structure(h2, h3, fmt_obj)
    s4 = score_author_bio(author_bio, author_url)
    s5 = score_nuance_markers(text, word_count)
    s6 = score_heading_diversity(all_headings)

    final_score = round(
        s1 * 0.25
        + s2 * 0.20
        + s3 * 0.20
        + s4 * 0.15
        + s5 * 0.10
        + s6 * 0.10
    )

    flags: list[str] = []
    if s4 == 0:
        flags.append("no_author_bio")
    if s1 < 50:
        flags.append("insufficient_external_links")
    if s2 < 50:
        flags.append("no_cited_statistics")

    signals = {
        "external_links":    {"value": round(s1), "weight": 0.25, "contribution": round(s1 * 0.25, 1)},
        "cited_stats":       {"value": round(s2), "weight": 0.20, "contribution": round(s2 * 0.20, 1)},
        "heading_structure": {"value": round(s3), "weight": 0.20, "contribution": round(s3 * 0.20, 1)},
        "author_bio":        {"value": round(s4), "weight": 0.15, "contribution": round(s4 * 0.15, 1)},
        "nuance_markers":    {"value": round(s5), "weight": 0.10, "contribution": round(s5 * 0.10, 1)},
        "heading_diversity": {"value": round(s6), "weight": 0.10, "contribution": round(s6 * 0.10, 1)},
    }

    strengths = [k for k, v in signals.items() if v["value"] >= 75]
    weaknesses = [k for k, v in signals.items() if v["value"] < 50]
    explanation = (
        f"EEAT {fmt} : score {final_score}/100. "
        + (f"Points forts : {', '.join(strengths)}. " if strengths else "")
        + (f"À améliorer : {', '.join(weaknesses)}." if weaknesses else "Aucune faiblesse majeure.")
    )

    available = sum(1 for v in [s1, s2, s3, s5, s6] if v is not None)
    confidence = "high" if available >= 4 else "medium"

    return {
        "score": final_score,
        "confidence": confidence,
        "method": "rules",
        "content_format": fmt,
        "signals": signals,
        "flags": flags,
        "explanation": explanation,
        "version": "2.1",
    }


def check_eeat_dict(content: str | None, sources: list[str] | None = None, author_name: str | None = None) -> dict:
    """Legacy compatibility wrapper."""
    article = {"content": content or ""}
    result = compute_eeat_score(article)
    return {
        "score": result["score"],
        "checks": [],
        "passed": [],
        "failed": result["flags"],
        "recommendations": [],
        "manual_review_needed": result["score"] < 60,
        "v2": result,
    }
