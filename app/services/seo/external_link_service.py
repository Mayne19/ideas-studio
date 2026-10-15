from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from app.schemas.seo_workflow import ExternalLinkPlan, asdict
from app.services.seo.adapters.scrapling_adapter import scrapling_adapter
from app.services.seo.source_quality_service import classify_source_quality

logger = logging.getLogger(__name__)


# Hôtes qui ne sont jamais une source citable : raccourcisseurs, redirecteurs,
# régies publicitaires, pages de consentement ou de compte.
_JUNK_HOSTS = {
    "t.co", "bit.ly", "goo.gl", "lnkd.in", "ow.ly", "buff.ly", "tinyurl.com", "rebrand.ly",
    "doubleclick.net", "googleadservices.com", "googlesyndication.com", "l.facebook.com",
    "lm.facebook.com", "out.reddit.com", "wa.me", "api.whatsapp.com", "webcache.googleusercontent.com",
    "accounts.google.com", "consent.google.com", "policies.google.com", "myaccount.google.com",
    "translate.google.com", "maps.google.com", "news.google.com", "bing.com", "search.yahoo.com",
    "duckduckgo.com", "qwant.com", "ecosia.org", "yandex.ru", "yandex.com", "baidu.com",
}
# Moteurs de recherche : la racine (google.fr, www.google.com…) ne mène qu'à
# des pages de résultats ou de préférences.
_SEARCH_ENGINE_ROOT_RE = re.compile(r"^(?:www\.)?google\.[a-z.]{2,6}$")
# Chemins de recherche, de redirection, de partage ou de préférences.
_JUNK_PATH_RE = re.compile(
    r"^/(?:(?:url|redirect|out|click|share|sharer|intent|sharearticle|pin/create)(?:[/.]|$)"
    r"|(?:search|preferences|setprefs|advanced_search|login|signin|signup|cart|checkout)(?:/?$|\.))",
    re.IGNORECASE,
)
# Paramètres qui trahissent une page de résultats ou une redirection.
_JUNK_QUERY_KEYS = {"q", "query", "search", "s", "url", "u", "redirect", "redirect_uri", "dest", "target"}
_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid", "_ga", "msclkid")


def is_junk_url(url: str) -> bool:
    """Vrai pour une URL qui ne peut pas servir de source à un lecteur :
    page de recherche ou de préférences, redirection, raccourcisseur,
    tracking publicitaire, bouton de partage."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return True
    host = (parsed.hostname or "").lower()
    bare = host.removeprefix("www.")
    if bare in _JUNK_HOSTS or bare.endswith(".doubleclick.net"):
        return True
    if _SEARCH_ENGINE_ROOT_RE.match(host):
        return True
    if _JUNK_PATH_RE.match(parsed.path or "/"):
        return True
    keys = {p.split("=", 1)[0].lower() for p in (parsed.query or "").split("&") if p}
    return bool(keys & _JUNK_QUERY_KEYS)


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
    if is_junk_url(url):
        return None
    # Normalise : minuscules pour schéma/domaine, suppression fragment + tracking
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    query_parts = [p for p in parsed.query.split("&") if p and not p.startswith(_TRACKING_PREFIXES)]
    query = "&".join(query_parts)
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


def _clean_excerpt(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


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


def _host_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _is_subject_official_host(host: str, keyword: str) -> bool:
    """Site officiel d'une entité nommée dans le mot-clé (webflow.com pour
    « webflow ou wordpress ») : sa page tarifs ou sa doc est une source
    primaire, pas un article concurrent."""
    parts = host.split(".")
    if len(parts) < 2:
        return False
    brand = parts[-2]
    tokens = {t for t in re.split(r"[^\w]+", (keyword or "").lower()) if len(t) >= 4}
    return brand in tokens


def _serp_competitor_hosts(sources: list, keyword: str = "") -> set[str]:
    """Domaines des résultats SERP du mot-clé : ce sont les concurrents
    directs de l'article. Les sources de référence (Wikipédia, sites publics…
    classées 'strong') et les sites officiels des entités du mot-clé restent
    citables même s'ils rankent sur le mot-clé."""
    hosts: set[str] = set()
    for src in sources:
        if not isinstance(src, dict):
            continue
        url = src.get("url") or ""
        host = _host_of(url)
        if not host or classify_source_quality(url) == "strong" or _is_subject_official_host(host, keyword):
            continue
        hosts.add(host)
    return hosts


def _is_serp_competitor(url: str, competitor_hosts: set[str]) -> bool:
    host = _host_of(url)
    return bool(host) and any(host == h or host.endswith("." + h) for h in competitor_hosts)


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
    # Ne jamais renvoyer le lecteur vers un concurrent qui ranke sur le même
    # mot-clé (ni vers une autre page de son site découverte en le scrapant).
    serp_hosts = _serp_competitor_hosts(sources, keyword)

    # URLs découvertes par Scrapling chez les concurrents (anciens briefs :
    # elles étaient stockées dans facts_to_include).
    discovered_urls: list[str] = [
        url for url in (research.get("discovered_links") or []) + (research.get("facts_to_include") or [])
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
        if _is_serp_competitor(url, serp_hosts):
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
            "domain_tier": classify_source_quality(url),
            # Extrait de la page : permet au writer de ne citer la source que
            # sur une phrase que cet extrait soutient réellement.
            "excerpt": _clean_excerpt(src.get("snippet") or src.get("meta_description") or ""),
            "nofollow_recommended": True,
            "word_count": quality_check.get("word_count", 0),
        })

    # Add discovered external links (deduplicated)
    for url in discovered_urls:
        clean_url = _clean_url(url)
        if not clean_url or clean_url in seen_urls or _is_competitor_domain(clean_url, competitor_domains):
            continue
        if _is_serp_competitor(clean_url, serp_hosts):
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
            "domain_tier": classify_source_quality(clean_url),
            "excerpt": "",
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
    tier_rank = {"strong": 2, "neutral": 1, "weak": 0}

    def _rank(link: dict) -> tuple:
        # Sources de référence et liens accompagnés d'un extrait d'abord.
        return (
            tier_rank.get(link.get("domain_tier", "neutral"), 1),
            bool(link.get("excerpt")),
            link.get("word_count", 0),
            _path_depth(link.get("url", "")),
        )

    for link in sorted(candidate_links, key=_rank, reverse=True):
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
