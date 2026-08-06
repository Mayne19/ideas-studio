from __future__ import annotations

import logging
from time import perf_counter
from urllib.parse import urlparse

from app.services.seo.adapters.scrapling_adapter import scrapling_adapter

logger = logging.getLogger(__name__)

_MIN_WORD_COUNT = 150

# ─────────────────────────────────────────────────────────────────────────────
# Classification de fiabilité des domaines (source_quality_checker, étape 6b).
# Une seule source de vérité pour toute la chaîne : `validate_sources()` attache
# le tier à chaque source validée, et `eeat_service.score_external_links()`
# l'utilise pour pondérer les liens externes de l'article (score EEAT). Ne pas
# dupliquer cette logique ailleurs — la remplacer ici répercute le changement
# partout.
#
# Sources fortes : gouvernements (.gouv/.gov/.edu…), organismes officiels et
# instituts de statistiques (INSEE…), encyclopédies de référence, grands médias
# établis → score plein ou bonus.
# Sources neutres : sites d'entreprises, blogs spécialisés reconnus → score
# standard.
# Sources faibles : réseaux sociaux génériques, pages de recherche/résultats
# (ex. reddit.com/search), forums non modérés, contenus sans auteur identifiable
# → pénalité claire.
# ─────────────────────────────────────────────────────────────────────────────

STRONG_SOURCE_SUFFIXES = (
    ".gouv.fr", ".gouv.qc.ca", ".gouv.mc", ".gov", ".gov.uk", ".gov.br",
    ".gov.au", ".gc.ca", ".edu", ".edu.br", ".ac.uk", ".edu.au", ".ac.at",
    ".ac.fr", ".int", ".europa.eu", ".europe.eu",
)

# Domaines exacts (hors www.) — organismes officiels / instituts / médias établis
STRONG_SOURCE_DOMAINS = {
    # Organismes officiels et instituts
    "insee.fr", "ined.fr", "ireps.fr", "drees.solidarites-sante.gouv.fr",
    "service-public.fr", "data.gouv.fr", "vie-publique.fr", "legifrance.gouv.fr",
    "banque-france.fr", "courdecassation.fr", "courdescomptes.fr",
    "conseil-constitutionnel.fr", "conseil-etat.fr", "assemblee-nationale.fr",
    "senat.fr", "ameli.fr", "pole-emploi.fr", "caissedesdepots.fr",
    "coe.int", "un.org", "unicef.org", "who.int", "imf.org", "worldbank.org",
    "banquemondiale.org", "oecd.org", "ocde.org", "ilo.org", "fao.org",
    "unesco.org", "ecb.europa.eu",
    # Encyclopédies de référence
    "wikipedia.org", "britannica.com",
    # Grands médias établis (France)
    "lemonde.fr", "lefigaro.fr", "lesechos.fr", "liberation.fr", "leparisien.fr",
    "francetvinfo.fr", "france24.com", "franceinter.fr", "rfi.fr", "bfmtv.com",
    "lexpress.fr", "lepoint.fr", "courrierinternational.com", "mediapart.fr",
    "nouvelobs.com", "lci.fr", "lejdd.fr", "ouest-france.fr",
    "sudouest.fr", "ladepeche.fr", "la-croix.com", "humanite.fr",
    # Grands médias établis (international)
    "nytimes.com", "bbc.com", "bbc.co.uk", "reuters.com", "apnews.com",
    "afp.com", "theguardian.com", "ft.com", "wsj.com", "bloomberg.com",
    "economist.com", "washingtonpost.com", "cnn.com", "npr.org", "theverge.com",
}

# Domaines faibles — réseaux sociaux génériques, agrégateurs de recherche,
# Q&A non modérés, forums, contenu utilisateur sans auteur identifiable
WEAK_SOURCE_DOMAINS = {
    "reddit.com", "facebook.com", "fb.com", "instagram.com", "twitter.com",
    "x.com", "tiktok.com", "linkedin.com", "pinterest.com", "pinterest.fr",
    "youtube.com", "youtu.be", "snapchat.com", "tumblr.com",
    "quora.com", "answers.com", "ask.com", "answers.yahoo.com", "yandex.ru",
    "google.com", "google.fr", "duckduckgo.com", "bing.com", "qwant.com",
    "startpage.com", "yahoo.com", "search.yahoo.com",
    "tripadvisor.fr", "tripadvisor.com", "yelp.com", "trustpilot.com",
    "glassdoor.com", "glassdoor.fr", "4chan.org", "8kun.top",
}

WEAK_SOURCE_SUBSTRINGS = ("forum", "forums", "discuss", "boards")


def classify_source_quality(url: str) -> str:
    """Classe la fiabilité d'un domaine source — 'strong', 'neutral' ou 'weak'.
    Basé sur le domaine et le TLD ; ne fait aucun appel réseau (la disponibilité
    et le volume de contenu sont déjà couverts par validate_url()). Les
    sous-domaines d'un domaine classé sont hérités de sa classe (fr.wikipedia.org,
    old.reddit.com, forums.gouv.fr…)."""
    if not url or not isinstance(url, str):
        return "neutral"
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return "neutral"
    if not host:
        return "neutral"
    host = host.removeprefix("www.")

    def _in_set(host: str, domains: set[str]) -> bool:
        return host in domains or any(host.endswith("." + d) for d in domains)

    if _in_set(host, STRONG_SOURCE_DOMAINS) or any(host.endswith(s) for s in STRONG_SOURCE_SUFFIXES):
        return "strong"
    if _in_set(host, WEAK_SOURCE_DOMAINS):
        return "weak"
    if any(sub in host for sub in WEAK_SOURCE_SUBSTRINGS):
        return "weak"
    return "neutral"

# Jusqu'à 12 sources validées séquentiellement (~8s max chacune côté
# scrapling_adapter) : sans budget global, une série de sources lentes ou
# bloquées (ex. rate-limiting réseau côté hébergeur) pouvait faire dériver
# cette seule étape vers plusieurs minutes. On plafonne le temps total et on
# marque les sources restantes comme "skipped" plutôt que de les bloquer.
SOURCE_VALIDATION_TIME_BUDGET_SECONDS = 30


def validate_sources(sources: list[dict]) -> list[dict]:
    """
    For each source dict (must have a 'url' key), verify reachability and
    content quality via Scrapling. Returns a new list with a 'quality_check'
    sub-dict added to each entry.
    """
    if not scrapling_adapter.configured:
        return [
            {**src, "quality_check": {"skipped": True, "reason": "scrapling_not_configured"}}
            for src in sources
        ]

    validated = []
    started_at = perf_counter()
    for src in sources:
        if perf_counter() - started_at > SOURCE_VALIDATION_TIME_BUDGET_SECONDS:
            logger.warning(
                "source_quality: budget de %ss dépassé, %s source(s) restante(s) sautée(s)",
                SOURCE_VALIDATION_TIME_BUDGET_SECONDS, len(sources) - len(validated),
            )
            validated.append({**src, "quality_check": {"skipped": True, "reason": "time_budget_exceeded"}})
            continue
        url = src.get("url", "")
        if not url:
            validated.append({**src, "quality_check": {"skipped": True, "reason": "no_url"}})
            continue
        check = scrapling_adapter.validate_url(url)
        quality = {
            "reachable": check.get("reachable", False),
            "word_count": check.get("word_count", 0),
            "quality": check.get("quality", "unknown"),
            "reliable": check.get("reachable", False) and check.get("word_count", 0) >= _MIN_WORD_COUNT,
            "source_tier": classify_source_quality(url),
        }
        if not quality["reachable"]:
            quality["error"] = check.get("error", "unreachable")
        validated.append({**src, "quality_check": quality})
        logger.debug("source_quality %s → %s", url, quality["quality"])

    return validated


def filter_reliable_sources(sources: list[dict]) -> list[dict]:
    """Return only sources that passed quality validation."""
    return [s for s in sources if s.get("quality_check", {}).get("reliable", False)]
