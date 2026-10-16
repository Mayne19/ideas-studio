from __future__ import annotations

"""A2 Research Reader, partie lecture (chaîne v2, étape 5).

Lit en entier le top 5 organique et jusqu'à 4 sources primaires (site
officiel d'une entité du mot-clé, .gouv, documentation, page tarifs) trouvées
par des requêtes dédiées (search_primary_candidates) puis dans les résultats. Les pages passent par le PageCache de la génération : une
URL déjà téléchargée par le research brief n'est pas retéléchargée. Le texte
principal (trafilatura) est tronqué à MAX_CHARS_PER_PAGE et stocké dans
l'artefact `source_pages`, matière première du fact_ledger.
"""

import logging
import re
from time import perf_counter
from urllib.parse import urlparse

from app.services.seo.page_cache import PageCache, active_page_cache

logger = logging.getLogger(__name__)

TOP_ORGANIC = 5
MAX_PRIMARY = 4
# Requêtes dédiées aux sources primaires : le top organique d'un mot-clé
# commercial ne contient presque que des blogs concurrents (exclus des
# citations), d'où des faits sans source citable.
PRIMARY_QUERIES = (
    "{keyword} site:gouv.fr OR site:insee.fr OR site:europa.eu",
    "{keyword} étude chiffres officiels",
)
MAX_CHARS_PER_PAGE = 12_000
TIME_BUDGET_SECONDS = 40
_PRIMARY_HOST_PREFIXES = ("docs.", "developer.", "developers.", "help.", "support.")
# Organismes officiels et instituts : sources primaires (les grands médias,
# classés « strong » eux aussi, n'en sont pas).
_OFFICIAL_BODIES = {
    "insee.fr", "ined.fr", "service-public.fr", "data.gouv.fr", "vie-publique.fr", "ameli.fr",
    "banque-france.fr", "courdescomptes.fr", "conseil-etat.fr", "assemblee-nationale.fr", "senat.fr",
    "who.int", "oecd.org", "ocde.org", "imf.org", "worldbank.org", "un.org", "unesco.org", "ilo.org",
}


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def is_primary_source(url: str, keyword: str = "") -> bool:
    """Source primaire : organisme officiel (.gouv, .edu, institut…), site
    officiel d'une entité nommée dans le mot-clé (webflow.com pour « prix
    webflow »), ou sous-domaine de documentation / support d'un éditeur."""
    from app.services.seo.external_link_service import _is_subject_official_host
    from app.services.seo.source_quality_service import STRONG_SOURCE_SUFFIXES, classify_source_quality

    host = _host(url)
    if not host or classify_source_quality(url) == "weak":
        return False
    if any(host.endswith(s) for s in STRONG_SOURCE_SUFFIXES):
        return True
    if host in _OFFICIAL_BODIES or any(host.endswith("." + o) for o in _OFFICIAL_BODIES):
        return True
    if _is_subject_official_host(host, keyword):
        return True
    return host.startswith(_PRIMARY_HOST_PREFIXES)


def search_primary_candidates(keyword: str, search_fn, limit: int = 8) -> list[tuple[str, str]]:
    """[(url, titre)] des sources primaires trouvées par PRIMARY_QUERIES.
    `search_fn(query, limit) -> [{url|link, title}]` ; une requête en échec
    est ignorée."""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for template in PRIMARY_QUERIES:
        try:
            results = search_fn(template.format(keyword=keyword), limit) or []
        except Exception as exc:
            logger.debug("source_pages: recherche primaire échouée : %s", exc)
            continue
        for r in results:
            if not isinstance(r, dict):
                continue
            url = r.get("url") or r.get("link") or ""
            if url and url not in seen and is_primary_source(url, keyword):
                seen.add(url)
                found.append((url, r.get("title", "")))
    return found


def select_source_urls(research_brief: dict, keyword: str, top_n: int = TOP_ORGANIC,
                       max_primary: int = MAX_PRIMARY,
                       extra_candidates: list[tuple[str, str]] | None = None) -> list[dict]:
    """[{url, role: competitor|primary, title}] : top N organiques puis
    jusqu'à `max_primary` sources primaires repérées dans le reste des
    résultats, les liens découverts, les PAA et l'encadré de réponse."""
    from app.services.seo.external_link_service import _clean_url

    research = research_brief or {}
    selected: list[dict] = []
    seen: set[str] = set()

    def _add(url: str, role: str, title: str = "") -> bool:
        clean = _clean_url(url or "")
        if not clean or clean in seen:
            return False
        seen.add(clean)
        selected.append({"url": clean, "role": role, "title": title})
        return True

    organic = [s for s in (research.get("sources_consulted") or []) if isinstance(s, dict) and s.get("url")]
    for src in organic[:top_n]:
        _add(src["url"], "competitor", src.get("title", ""))

    candidates: list[tuple[str, str]] = list(extra_candidates or [])
    candidates += [(s["url"], s.get("title", "")) for s in organic[top_n:]]
    candidates += [(u, "") for u in research.get("discovered_links") or [] if isinstance(u, str)]
    candidates += [(q.get("url", ""), q.get("title", "")) for q in research.get("people_also_ask") or []
                   if isinstance(q, dict)]
    box = research.get("answer_box") or {}
    if box.get("url"):
        candidates.append((box["url"], box.get("title", "")))
    graph = research.get("knowledge_graph") or {}
    if graph.get("url"):
        candidates.append((graph["url"], graph.get("title", "")))

    primaries = 0
    for url, title in candidates:
        if primaries >= max_primary:
            break
        if url and is_primary_source(url, keyword) and _add(url, "primary", title):
            primaries += 1
    return selected


def _truncate(text: str, limit: int) -> str:
    text = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    # Coupe sur une fin de phrase si possible, pour garder des citations entières.
    end = max(cut.rfind(". "), cut.rfind(".\n"))
    return cut[: end + 1] if end > limit * 0.7 else cut


def build_source_pages(
    research_brief: dict,
    keyword: str,
    cache: PageCache | None = None,
    *,
    max_chars: int = MAX_CHARS_PER_PAGE,
    extractor=None,
    time_budget: float = TIME_BUDGET_SECONDS,
    search_fn=None,
) -> dict:
    """Artefact `source_pages` : {pages: [{url, role, title, text, chars,
    word_count, source_tier, method}], skipped: [{url, reason}], fetch_stats}."""
    from app.services.seo.source_quality_service import classify_source_quality

    if extractor is None:
        from app.services.seo.adapters.content_extraction_adapter import content_extraction_adapter
        extractor = content_extraction_adapter
    cache = cache or active_page_cache() or PageCache()
    pages: list[dict] = []
    skipped: list[dict] = []
    started = perf_counter()
    extra = search_primary_candidates(keyword, search_fn) if search_fn else []
    for item in select_source_urls(research_brief, keyword, extra_candidates=extra):
        url = item["url"]
        if perf_counter() - started > time_budget:
            skipped.append({"url": url, "reason": "time_budget_exceeded"})
            continue
        html = cache.get_html(url)
        if not html:
            reason = "robots_disallow" if url in cache.blocked_by_robots else "fetch_failed"
            skipped.append({"url": url, "reason": reason})
            continue
        try:
            extracted = extractor.extract_from_html(html, url)
        except Exception as exc:
            logger.debug("source_pages: extraction échouée %s : %s", url, exc)
            extracted = None
        if not extracted or not extracted.get("text"):
            skipped.append({"url": url, "reason": "no_main_text"})
            continue
        text = _truncate(extracted["text"], max_chars)
        pages.append({
            "url": url,
            "role": item["role"],
            "title": extracted.get("title") or item.get("title") or "",
            "text": text,
            "chars": len(text),
            "word_count": len(re.findall(r"\w+", extracted["text"])),
            "source_tier": classify_source_quality(url),
            "method": extracted.get("method", ""),
        })
    return {"pages": pages, "skipped": skipped, "fetch_stats": cache.stats(), "max_chars_per_page": max_chars}
