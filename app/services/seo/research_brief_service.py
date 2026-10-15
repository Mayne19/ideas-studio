from __future__ import annotations

import logging
import re
from time import perf_counter
from urllib.parse import urlparse

from app.schemas.seo_workflow import ResearchBrief, asdict
from app.services.seo.adapters.serp_adapter import serp_adapter
from app.services.seo.adapters.scrapling_adapter import scrapling_adapter

logger = logging.getLogger(__name__)

# Jusqu'à 12 URLs SERP scrapées séquentiellement (~8s max chacune côté
# scrapling_adapter) avant même le début de la rédaction : sans budget
# global, des sources lentes ou bloquées côté réseau pouvaient faire dériver
# cette seule étape vers plusieurs minutes. Au-delà du budget, les URLs
# restantes retombent sur le snippet SERP seul (déjà le comportement de
# fallback existant en cas d'échec de scrape).
RESEARCH_BRIEF_TIME_BUDGET_SECONDS = 30

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
# Un fait exploitable contient un chiffre (prix, part de marché, date, durée).
_FIGURE_RE = re.compile(r"\d")
_MAX_FACTS = 8


def extract_facts_from_snippets(sources: list[dict], limit: int = _MAX_FACTS) -> list[str]:
    """Faits courts tirés des snippets SERP / meta descriptions : une phrase
    complète contenant un chiffre, suivie de son domaine source. Jamais d'URL
    nue ; liste vide si aucun snippet ne contient de fait précis."""
    facts: list[str] = []
    seen: set[str] = set()
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        host = (urlparse(src.get("url") or "").hostname or "").removeprefix("www.")
        text = " ".join(
            str(src.get(k) or "") for k in ("snippet", "meta_description")
        )
        for sentence in _SENTENCE_SPLIT_RE.split(re.sub(r"\s+", " ", text).strip()):
            sentence = sentence.strip(" .…-")
            words = sentence.split()
            if not (6 <= len(words) <= 40) or not _FIGURE_RE.search(sentence):
                continue
            if _URL_RE.search(sentence) or "..." in sentence:
                continue
            key = sentence.lower()
            if key in seen:
                continue
            seen.add(key)
            facts.append(f"{sentence} (source : {host})" if host else sentence)
            if len(facts) >= limit:
                return facts
    return facts


def build_research_brief(
    keyword: str,
    title: str | None = None,
    category_name: str | None = None,
    serp_enabled: bool = False,
    project_id: str | None = None,
) -> ResearchBrief:
    brief = ResearchBrief()

    if not serp_adapter.configured:
        brief.research_status = "not_available"
        brief.limitations = [
            "SERP provider not configured (SERPER_API_KEY or SERP_API_KEY missing)",
            "Research based on internal context only, no real competitor analysis",
        ]
        return brief

    results = serp_adapter.search(keyword, limit=12)
    if not results:
        brief.research_status = "not_available"
        brief.limitations = ["SERP returned no results"]
        return brief

    brief.research_status = "available"
    external_links_discovered: list[dict] = []
    started_at = perf_counter()
    budget_exceeded = False

    for r in results:
        url = r.get("url", "")
        if not url:
            continue

        if budget_exceeded or perf_counter() - started_at > RESEARCH_BRIEF_TIME_BUDGET_SECONDS:
            if not budget_exceeded:
                budget_exceeded = True
                logger.warning(
                    "research_brief: budget de %ss dépassé, URLs restantes limitées au snippet SERP",
                    RESEARCH_BRIEF_TIME_BUDGET_SECONDS,
                )
            brief.sources_consulted.append({"url": url, "title": r.get("title", ""), "snippet": r.get("snippet", "")})
            continue

        # Scrapling full competitor scrape
        if scrapling_adapter.configured:
            competitor = scrapling_adapter.scrape_competitor(url)
            if "error" not in competitor:
                source_entry = {
                    "url": url,
                    "title": competitor.get("title") or r.get("title", ""),
                    "snippet": r.get("snippet", ""),
                    "word_count": competitor.get("word_count", 0),
                    "meta_description": competitor.get("meta_description", ""),
                }
                brief.sources_consulted.append(source_entry)

                for h in competitor.get("headings", []):
                    if h["level"] in (2, 3):
                        brief.competitor_angles.append(
                            f"{h['text']} (from {competitor.get('title') or r.get('title', url)})"
                        )

                for lk in competitor.get("external_links_discovered", []):
                    if lk not in external_links_discovered:
                        external_links_discovered.append(lk)
            else:
                # Fallback: use SERP snippet only
                brief.sources_consulted.append({"url": url, "title": r.get("title", ""), "snippet": r.get("snippet", "")})
        else:
            brief.sources_consulted.append({"url": url, "title": r.get("title", ""), "snippet": r.get("snippet", "")})

    # Attach discovered external links as a field_signal for the orchestrator
    if external_links_discovered:
        brief.field_signals.append(
            f"{len(external_links_discovered)} liens externes découverts chez les concurrents"
        )
    # URLs brutes pour ExternalLinkPlan : jamais dans facts_to_include, qui ne
    # contient que des faits lisibles par le writer.
    brief.discovered_links.extend(
        [lk.get("url", "") for lk in external_links_discovered[:10] if lk.get("url")]
    )
    brief.facts_to_include.extend(extract_facts_from_snippets(brief.sources_consulted))

    brief.limitations.append("SERP research used limited results (12 URLs max)")
    if budget_exceeded:
        brief.limitations.append(
            f"Budget de temps ({RESEARCH_BRIEF_TIME_BUDGET_SECONDS}s) dépassé — certaines URLs n'ont pas été scrapées en détail"
        )
    return brief


def build_research_brief_dict(
    keyword: str,
    title: str | None = None,
    category_name: str | None = None,
    serp_enabled: bool = False,
    project_id: str | None = None,
) -> dict:
    return asdict(build_research_brief(keyword, title, category_name, serp_enabled, project_id))
