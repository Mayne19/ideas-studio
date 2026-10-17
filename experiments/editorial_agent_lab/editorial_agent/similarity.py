"""Alerte de plagiat, sans réécriture : phrases de l'article (au moins 8 mots)
présentes telles quelles dans une page source."""

from __future__ import annotations

import re
from html import unescape
from typing import Callable


def _plain(text: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text or "", flags=re.IGNORECASE | re.DOTALL)
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", text)).split()).lower()


def _sentences(markdown: str) -> list[str]:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown)  # liens Markdown : on garde l'ancre
    text = re.sub(r"[#*_`>|]", " ", re.sub(r"<[^>]+>", "\n", text))
    sentences = []
    for line in text.splitlines():  # un titre ou un bloc ne se colle pas à la phrase suivante
        sentences += [s.strip() for s in re.split(r"(?<=[.!?])\s+", " ".join(line.split())) if s.strip()]
    return sentences


def scan_exact_phrases(article: str, sources: dict[str, str], min_words: int = 8) -> list[dict]:
    findings = []
    plain_sources = {url: _plain(text) for url, text in sources.items()}
    for sentence in _sentences(article):
        if len(sentence.split()) < min_words:
            continue
        normalized = " ".join(sentence.split()).lower()
        for url, source_text in plain_sources.items():
            if normalized in source_text:
                findings.append({"sentence": sentence, "source_url": url})
                break
    return findings


def fetch_text(url: str, timeout: float = 15.0) -> str:
    import httpx

    resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/605.1.15 Safari/605.1.15"})
    return resp.text if resp.status_code < 400 else ""


def plagiarism_alert(article: str, source_urls: list[str], fetch: Callable[[str], str] = fetch_text) -> dict:
    texts, unreadable = {}, []
    for url in source_urls:
        try:
            texts[url] = fetch(url) or ""
        except Exception:  # noqa: BLE001 - une source illisible n'empêche pas l'alerte
            texts[url] = ""
        if not texts[url]:
            unreadable.append(url)
    findings = scan_exact_phrases(article, texts)
    return {"name": "plagiat (alerte)", "blocking": False, "findings": findings, "unreadable_sources": unreadable}
