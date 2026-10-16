"""Contrôle anti-plagiat de l'article final : une phrase de 12 mots ou plus
environ tous les 150 mots, cherchée entre guillemets ; une phrase est
plagiée si un extrait de résultat en reprend au moins 10 mots consécutifs.

Le moteur de recherche est un fournisseur interchangeable
(`PlagiarismBackend`) : la recherche SERP par défaut, un service dédié
(Copyleaks, Originality.ai…) plus tard sans changer l'appelant.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Callable, Protocol
from urllib.parse import urlparse

from app.services.seo.html_text_ops import html_to_text, split_units, text_blocks, unit_heading

logger = logging.getLogger(__name__)

SearchFn = Callable[[str, int], list[dict]]
MAX_SENTENCES = 12
WORDS_BETWEEN_SAMPLES = 150
MIN_SENTENCE_WORDS = 12
MIN_MATCH_WORDS = 10
RESULTS_PER_QUERY = 5

# Titres, tableaux et citations : jamais testés (une citation est reprise
# volontairement, un titre ou une cellule n'est pas une phrase).
_EXCLUDED_RE = re.compile(
    r"<(h[1-6]|table|blockquote|q|figcaption)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")


class PlagiarismBackend(Protocol):
    name: str

    def check(self, sentences: list[str]) -> list[dict]:
        """Une entrée par correspondance : {sentence, url, matched_words, matched_count}."""
        ...


def _words(text: str) -> list[str]:
    """Mots normalisés : minuscules, sans accents ni ponctuation."""
    text = unicodedata.normalize("NFKD", (text or "").lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).split()


def _sentences(content: str) -> list[str]:
    text_html = _EXCLUDED_RE.sub(" ", content or "")
    found = []
    for block in text_blocks(text_html):
        block = re.sub(r"\s+([,.])", r"\1", block)
        found += [s.strip() for s in _SENTENCE_SPLIT_RE.split(block) if s.strip()]
    return found


def extract_sentences(content: str, max_sentences: int = MAX_SENTENCES) -> list[str]:
    """Une phrase de MIN_SENTENCE_WORDS mots ou plus environ tous les
    WORDS_BETWEEN_SAMPLES mots, au plus `max_sentences`."""
    picked: list[str] = []
    position, next_at = 0, 0
    for sentence in _sentences(content):
        count = len(sentence.split())
        if position >= next_at and count >= MIN_SENTENCE_WORDS:
            picked.append(sentence)
            next_at = position + WORDS_BETWEEN_SAMPLES
            if len(picked) >= max_sentences:
                break
        position += count
    return picked


def longest_common_run(sentence: str, snippet: str) -> list[str]:
    """Plus longue suite de mots consécutifs identiques (après normalisation)."""
    a, b = _words(sentence), _words(snippet)
    best_len, best_end = 0, 0
    previous = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        current = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                current[j] = previous[j - 1] + 1
                if current[j] > best_len:
                    best_len, best_end = current[j], i
        previous = current
    return a[best_end - best_len: best_end]


def _host(url: str) -> str:
    value = (url or "").strip().lower()
    if "://" not in value:
        value = "//" + value
    host = urlparse(value).hostname or ""
    return host[4:] if host.startswith("www.") else host


def is_own_domain(url: str, own_domain: str) -> bool:
    own = _host(own_domain)
    host = _host(url)
    return bool(own) and (host == own or host.endswith("." + own))


class SerpPlagiarismBackend:
    """Recherche exacte (phrase entre guillemets) via l'adaptateur SERP."""
    name = "serp"

    def __init__(self, search_fn: SearchFn, *, own_domain: str = "", limit: int = RESULTS_PER_QUERY):
        self.search_fn = search_fn
        self.own_domain = own_domain or ""
        self.limit = limit
        self.errors: list[str] = []

    def _search(self, sentence: str) -> list[dict]:
        try:
            return self.search_fn(f'"{sentence}"', self.limit) or []
        except Exception as exc:
            # Une recherche en échec n'est pas un plagiat : on note et on continue.
            self.errors.append(f"{sentence[:60]} : {exc}"[:300])
            return []

    def _match(self, sentence: str, result: dict) -> dict | None:
        url = str(result.get("url") or result.get("link") or "")
        if is_own_domain(url, self.own_domain):
            return None
        run = longest_common_run(sentence, f"{result.get('title') or ''} … {result.get('snippet') or ''}")
        if len(run) < MIN_MATCH_WORDS:
            return None
        return {"sentence": sentence, "url": url, "matched_words": " ".join(run), "matched_count": len(run)}

    def check(self, sentences: list[str]) -> list[dict]:
        matches = []
        for sentence in sentences:
            for result in self._search(sentence):
                match = self._match(sentence, result) if isinstance(result, dict) else None
                if match:
                    matches.append(match)
                    break
        return matches


def check_plagiarism(content: str, backend: PlagiarismBackend | None,
                     sentences: list[str] | None = None) -> dict:
    """Rapport : statut (clean, plagiarism, skipped), phrases testées, correspondances."""
    if backend is None:
        return {"status": "skipped", "reason": "aucun moteur de recherche configuré", "sentences": [], "matches": []}
    tested = extract_sentences(content) if sentences is None else sentences[:MAX_SENTENCES]
    matches = backend.check(tested)
    report = {
        "status": "plagiarism" if matches else "clean",
        "backend": getattr(backend, "name", ""),
        "sentences": tested,
        "matches": matches,
    }
    errors = getattr(backend, "errors", None)
    if errors:
        report["errors"] = list(errors)
    return report


def plagiarism_fixes(content: str, sentences: list[str]) -> list[dict]:
    """Une consigne de révision par section contenant une phrase plagiée."""
    by_section: dict[str, list[str]] = {}
    units = split_units(content)
    for sentence in sentences:
        for index, unit in enumerate(units):
            if sentence in re.sub(r"\s+([,.])", r"\1", html_to_text(unit)):
                section = "INTRODUCTION" if index == 0 else unit_heading(unit)
                by_section.setdefault(section, []).append(sentence)
                break
    return [
        {"section": section, "instructions": " ".join(
            f"Reformule entièrement cette phrase, même sens, autres mots : « {s} »" for s in found)}
        for section, found in by_section.items()
    ]


def retest_candidates(before: str, after: str, matched: list[str]) -> list[str]:
    """Phrases à retester après réécriture : les nouvelles phrases et les
    phrases plagiées encore présentes."""
    old = set(_sentences(before))
    return [
        s for s in _sentences(after)
        if (s not in old and len(s.split()) >= MIN_SENTENCE_WORDS) or s in matched
    ][:MAX_SENTENCES]


def plagiarism_blocker(matches: list[dict]) -> dict:
    detail = " | ".join(f"« {m['sentence'][:120]} » ({m['url']})" for m in matches[:3])
    return {"type": "plagiarism", "section": "", "detail": f"Phrase(s) reprise(s) mot pour mot : {detail}"[:600]}
