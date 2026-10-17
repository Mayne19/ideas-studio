"""Essai à blanc des outils de l'agent rédacteur, sans appel au modèle :
recherche du mot-clé (comme l'agent), recherches de sources officielles, puis
lecture de chaque URL avec le même lecteur que l'agent (directe, puis
secours). Le rapport donne pour chaque URL : statut, méthode, taille du HTML
brut, taille du texte, lecture réussie ou non, source admissible ou non.

Le coût se limite aux requêtes de recherche (Serper). Aucune liste de sources
n'est transmise à l'agent : ce script sert seulement à vérifier le lecteur.

Usage : DATABASE_URL=… SECRET_KEY=… python scripts/agent_tools_dry_run.py <project_id> "<mot-clé>"
        [--query "<requête de source>"]… [--max-urls 12] [--per-query 4] [--no-fallback]
"""
from __future__ import annotations

import argparse
import sys
from urllib.parse import urlsplit

# Domaines admissibles (règle de l'étape 4 du prompt) : institutions
# publiques, organismes techniques et scientifiques. Indicatif seulement.
ADMISSIBLE_SUFFIXES = (".gouv.fr", ".gov", ".gc.ca", ".europa.eu", ".who.int", ".nhs.uk", ".admin.ch", ".be")
ADMISSIBLE_HOSTS = {"ameli.fr", "anses.fr", "inserm.fr", "has-sante.fr", "santepubliquefrance.fr", "who.int",
                    "cnrs.fr", "pasteur.fr", "quechoisir.org", "60millions-mag.com", "test-achats.be",
                    "ginetex.net", "pubmed.ncbi.nlm.nih.gov", "cochranelibrary.com", "vidal.fr"}
SKIPPED_HOSTS = ("youtube.com", "facebook.com", "instagram.com", "tiktok.com", "reddit.com", "pinterest.")


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def admissible(url: str) -> bool:
    host = host_of(url)
    return host in ADMISSIBLE_HOSTS or any(host.endswith(s) for s in ADMISSIBLE_SUFFIXES)


def run(project_id: str, keyword: str, queries: list[str], max_urls: int, fallback: bool, per_query: int = 4) -> str:
    from app.services.seo.adapters.serp_adapter import get_serp_adapter
    from app.services.seo.agent_writer_openrouter import MIN_PAGE_CHARS, page_fetcher, reader_get
    from app.services.seo.page_cache import PageCache

    serp = get_serp_adapter(project_id)
    if not serp.configured:
        raise SystemExit("Recherche non configurée pour ce projet.")
    urls: list[str] = []
    for query in [keyword, *queries]:
        taken = 0
        for result in serp.search(query, 10) or []:
            url = result.get("url") or result.get("link") or ""
            if taken < per_query and url and url not in urls and not any(s in host_of(url) for s in SKIPPED_HOSTS):
                urls.append(url)
                taken += 1
    urls = urls[:max_urls]

    fetch = page_fetcher(PageCache(), fallback=reader_get if fallback else None)
    lines = [f"Essai à blanc : « {keyword} », {1 + len(queries)} recherche(s), {len(urls)} URL lue(s).", "",
             "| URL | statut | méthode | HTML brut | texte | lue | admissible |", "|---|---|---|---|---|---|---|"]
    readable_admissible: set[str] = set()
    for url in urls:
        text = fetch(url)
        info = fetch.last
        ok = len(text.strip()) >= MIN_PAGE_CHARS
        if ok and admissible(url):
            readable_admissible.add(host_of(url))
        note = f" ({info['note']})" if info.get("note") else ""
        lines.append(f"| {url} | {info.get('status')} | {info.get('method')}{note} | {info.get('html_chars')} | "
                     f"{len(text.strip())} | {'oui' if ok else 'non'} | {'oui' if admissible(url) else 'non'} |")
    verdict = "OK" if len(readable_admissible) >= 3 else "INSUFFISANT"
    lines += ["", f"Domaines admissibles lisibles : {len(readable_admissible)} ({', '.join(sorted(readable_admissible))})",
              f"Verdict : {verdict} (il en faut au moins 3 avant l'essai payant)."]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id")
    parser.add_argument("keyword")
    parser.add_argument("--query", action="append", default=[])
    parser.add_argument("--max-urls", type=int, default=12)
    parser.add_argument("--per-query", type=int, default=4)
    parser.add_argument("--no-fallback", action="store_true")
    args = parser.parse_args()
    print(run(args.project_id, args.keyword, args.query, args.max_urls, not args.no_fallback, args.per_query))
    return 0


if __name__ == "__main__":
    sys.exit(main())
