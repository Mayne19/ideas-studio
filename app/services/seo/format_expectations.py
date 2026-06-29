from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FormatExpectations:
    min_external_links: int
    ideal_external_links: int
    min_h2_count: int
    ideal_h2_count: int
    faq_required: bool
    min_cited_stats: int
    ideal_cited_stats: int
    min_examples: int
    ideal_examples: int
    min_transition_density: float  # per 1000 words
    min_named_entities: int


FORMAT_EXPECTATIONS: dict[str, FormatExpectations] = {
    "short": FormatExpectations(
        min_external_links=1, ideal_external_links=2,
        min_h2_count=1, ideal_h2_count=2,
        faq_required=False,
        min_cited_stats=0, ideal_cited_stats=1,
        min_examples=1, ideal_examples=2,
        min_transition_density=1.0,
        min_named_entities=2,
    ),
    "medium": FormatExpectations(
        min_external_links=2, ideal_external_links=3,
        min_h2_count=2, ideal_h2_count=4,
        faq_required=False,
        min_cited_stats=1, ideal_cited_stats=2,
        min_examples=1, ideal_examples=3,
        min_transition_density=1.5,
        min_named_entities=4,
    ),
    "long": FormatExpectations(
        min_external_links=3, ideal_external_links=5,
        min_h2_count=4, ideal_h2_count=6,
        faq_required=True,
        min_cited_stats=2, ideal_cited_stats=4,
        min_examples=2, ideal_examples=4,
        min_transition_density=2.0,
        min_named_entities=6,
    ),
    "pillar": FormatExpectations(
        min_external_links=5, ideal_external_links=8,
        min_h2_count=6, ideal_h2_count=10,
        faq_required=True,
        min_cited_stats=3, ideal_cited_stats=6,
        min_examples=3, ideal_examples=6,
        min_transition_density=2.5,
        min_named_entities=10,
    ),
}

def infer_format(target_word_count: int | None) -> str:
    if not target_word_count:
        return "medium"
    if target_word_count < 800:
        return "short"
    if target_word_count < 1500:
        return "medium"
    if target_word_count < 2500:
        return "long"
    return "pillar"


def get_expectations(article: Any) -> FormatExpectations:
    if isinstance(article, dict):
        fmt = article.get("content_format") or infer_format(article.get("target_word_count"))
    else:
        fmt = getattr(article, "content_format", None) or infer_format(
            getattr(article, "target_word_count", None)
        )
    fmt = fmt or "medium"
    return FORMAT_EXPECTATIONS.get(fmt, FORMAT_EXPECTATIONS["medium"])


def get_format(article: Any) -> str:
    if isinstance(article, dict):
        fmt = article.get("content_format") or infer_format(article.get("target_word_count"))
    else:
        fmt = getattr(article, "content_format", None) or infer_format(
            getattr(article, "target_word_count", None)
        )
    return fmt or "medium"


def normalize_to_format(actual: float, minimum: float, ideal: float) -> float:
    """Score 0-100 relative to format expectations."""
    if ideal == 0:
        return 100.0
    if actual >= ideal:
        return 100.0
    if actual >= minimum:
        ratio = (actual - minimum) / (ideal - minimum)
        return round(50 + ratio * 50)
    ratio = actual / minimum if minimum > 0 else 0.0
    return round(ratio * 50)
