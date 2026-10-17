"""Analyse locale de similarité, sans modification du brouillon."""

from __future__ import annotations

import re
from html import unescape

from .models import SimilarityFinding


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def scan_exact_phrases(
    content: str,
    sources: dict[str, str],
    min_words: int = 8,
) -> list[SimilarityFinding]:
    """Signale les phrases identiques et propose une action séparée."""

    findings: list[SimilarityFinding] = []
    plain_content = unescape(re.sub(r"<[^>]+>", " ", content))
    for sentence in _sentences(plain_content):
        if len(sentence.split()) < min_words:
            continue
        normalized = " ".join(sentence.split()).lower()
        for url, source_text in sources.items():
            source_normalized = " ".join(source_text.split()).lower()
            if normalized in source_normalized:
                findings.append(SimilarityFinding(
                    sentence=sentence,
                    source_url=url,
                    matched_text=sentence,
                    similarity=1.0,
                    suggested_reformulation="Reformuler manuellement en conservant l'idée et la source.",
                ))
                break
    return findings
