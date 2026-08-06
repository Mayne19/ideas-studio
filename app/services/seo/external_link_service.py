from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.schemas.seo_workflow import ExternalLinkPlan, asdict
from app.services.seo.adapters.scrapling_adapter import scrapling_adapter

logger = logging.getLogger(__name__)


def _clean_url(url: str) -> str | None:
    """Normalise et filtre les URLs : majuscules de domaine, fragments, params
    de tracking supprimés, URLs invalides rejetées. Retourne None si l'URL ne
    peut pas être utilisée comme lien externe."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if not parsed.netloc or "." not in parsed.netloc:
        return None
    host = parsed.hostname or ""
    if host in ("example.com", "yourdomain.com", "domaine.com", "example.org"):
        return None
    # Normalise : minuscules pour schéma/domaine, suppression fragment + tracking
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    query_parts = [p for p in parsed.query.split("&") if p and not p.startswith(("utm_", "fbclid", "gclid"))]
    query = "&".join(query_parts)
    path = parsed.path
    clean = urlparse(url)._replace(scheme=scheme, netloc=netloc, query=query, fragment="").geturl()
    return clean


def _clean_anchor(anchor: str) -> str:
    """Nettoie le texte d'ancre : supprime les balises, majuscules en trop et
    les espaces multiples ; tronque pour rester un texte d'ancre raisonnable."""
    if not anchor:
        return "Source"
    import re
    anchor = re.sub(r"<[^>]+>", "", str(anchor))
    anchor = re.sub(r"\s+", " ", anchor).strip()
    if not anchor:
        return "Source"
    if anchor.lower().startswith(("http://", "https://", "www.")):
        return "Source"
    if len(anchor) > 80:
        anchor = anchor[:77].rstrip() + "…"
    return anchor


def _get_competitor_domains(db, project_id: str | None) -> set[str]:
    """Domaines à ne jamais proposer comme lien externe — lus depuis
    editorial_profiles.rules.competitor_domains (même champ JSON libre que
    image_plan_service.py, configurable par projet sans migration)."""
    if db is None or not project_id:
        return set()
    try:
        from app.models.core import Project
        project = db.get(Project, project_id)
        profile = project.active_editorial_profile if project else None
        domains = (profile.rules or {}).get("competitor_domains", []) if profile else []
        return {d.strip().lower() for d in domains if isinstance(d, str) and d.strip()}
    except Exception:
        return set()


def _is_competitor_domain(url: str, competitor_domains: set[str]) -> bool:
    if not competitor_domains:
        return False
    lowered = url.lower()
    return any(comp in lowered for comp in competitor_domains)


def build_external_link_plan(
    keyword: str,
    research_brief: dict | None = None,
    project_id: str | None = None,
    db=None,
) -> ExternalLinkPlan:
    plan = ExternalLinkPlan()
    competitor_domains = _get_competitor_domains(db, project_id)

    research = research_brief or {}
    sources = research.get("sources_consulted", [])

    # Also pick up URLs discovered by Scrapling during competitor scraping
    discovered_urls: list[str] = [
        url for url in research.get("facts_to_include", [])
        if isinstance(url, str) and url.startswith("http")
    ]

    candidate_links: list[dict] = []
    seen_urls: set[str] = set()

    for src in sources:
        if not isinstance(src, dict):
            continue
        url = _clean_url(src.get("url", ""))
        if not url or url in seen_urls or _is_competitor_domain(url, competitor_domains):
            continue
        seen_urls.add(url)
        quality_check = src.get("quality_check", {})
        if quality_check.get("skipped") or not quality_check.get("reliable", True):
            # Skip if explicitly validated and found unreliable
            if quality_check.get("reachable") is False:
                continue
        candidate_links.append({
            "url": url,
            "anchor_text": _clean_anchor(src.get("title", "Source")),
            "placement": "auto",
            "reason": "Source consultée lors de la recherche",
            "source_reliability": quality_check.get("quality", "medium"),
            "nofollow_recommended": True,
            "word_count": quality_check.get("word_count", 0),
        })

    # Add discovered external links (deduplicated)
    for url in discovered_urls:
        clean_url = _clean_url(url)
        if not clean_url or clean_url in seen_urls or _is_competitor_domain(clean_url, competitor_domains):
            continue
        seen_urls.add(clean_url)
        # Validate via Scrapling only if configured
        if scrapling_adapter.configured:
            check = scrapling_adapter.validate_url(clean_url)
            if not check.get("reachable"):
                continue
            quality = check.get("quality", "unknown")
            word_count = check.get("word_count", 0)
            # Ancre réelle : titre de la page cible plutôt que l'URL brute — un
            # lien externe dont l'ancre est l'URL nue (point 3 du pipeline) est
            # inexploitable pour un maillage naturel.
            anchor = _clean_anchor(check.get("title") or clean_url)
        else:
            quality = "unknown"
            word_count = 0
            anchor = _clean_anchor(clean_url)
        candidate_links.append({
            "url": clean_url,
            "anchor_text": anchor,
            "placement": "auto",
            "reason": "Lien découvert chez un concurrent",
            "source_reliability": quality,
            "nofollow_recommended": True,
            "word_count": word_count,
        })

    # URLs précises : une source à l'URL racine (ex: https://domaine.fr) est un
    # lien paresseux qui n'apporte rien de précis au lecteur — on privilégie les
    # URLs profondes (chemin significatif) et on diversifie les domaines (max 2
    # liens par domaine) pour que le maillage externe renvoie vers des pages
    # précises, pas vers trois pages du même site.
    def _path_depth(url: str) -> int:
        try:
            return len([s for s in urlparse(url).path.split("/") if s])
        except Exception:
            return 0

    def _domain_of(url: str) -> str:
        try:
            return (urlparse(url).hostname or "").lstrip("www.")
        except Exception:
            return ""

    domain_counts: dict[str, int] = {}
    diversified: list[dict] = []
    for link in sorted(candidate_links, key=lambda x: (x.get("word_count", 0), _path_depth(x.get("url", ""))), reverse=True):
        domain = _domain_of(link.get("url", ""))
        if domain_counts.get(domain, 0) >= 2:
            continue
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        diversified.append(link)
        if len(diversified) >= 8:
            break
    plan.links = diversified

    if not plan.links:
        plan.limitations = [
            "No external sources available",
            "SERP provider not configured for real research",
        ]
    else:
        if scrapling_adapter.configured:
            plan.limitations.append("Sources validated via Scrapling")

    return plan


def build_external_link_plan_dict(
    keyword: str,
    research_brief: dict | None = None,
    project_id: str | None = None,
    db=None,
) -> dict:
    return asdict(build_external_link_plan(keyword, research_brief, project_id, db))
