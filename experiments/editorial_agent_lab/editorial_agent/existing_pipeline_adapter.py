"""Adaptateurs de lecture seule vers les briques existantes d'Ideas Studio.

Le laboratoire dépend de ce module pour la recherche réelle, mais son cœur ne
importe ni `SerpAdapter` ni `PageCache`. Cela permet de tester l'algorithme avec
des faux fournisseurs et de garder une frontière nette avec le CMS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlsplit


SearchFn = Callable[[str, int], list[dict]]
FetchFn = Callable[[str], str]


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _url_key(url: str) -> str:
    try:
        parts = urlsplit((url or "").strip())
    except ValueError:
        return ""
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return ""
    return f"{_host(url)}{parts.path.rstrip('/') or '/'}"


@dataclass
class ExistingPipelineWebAdapter:
    """Expose la recherche et la lecture existantes sous le port du labo."""

    search_fn: SearchFn
    fetch_fn: FetchFn
    own_domain: str = ""
    search_limit: int = 10
    searches: int = 0
    pages_read: int = 0
    search_errors: list[str] = field(default_factory=list)
    fetch_errors: list[str] = field(default_factory=list)

    def search_competitors(self, keyword: str, domain: str = "", limit: int = 3) -> list[str]:
        """Sélectionne des URLs organiques uniques hors domaine propre."""

        own_host = _host(domain or self.own_domain)
        try:
            results = self.search_fn(keyword, self.search_limit) or []
        except Exception as exc:
            self.search_errors.append(str(exc))
            return []
        self.searches += 1
        selected: list[str] = []
        seen: set[str] = set()
        for result in results:
            if not isinstance(result, dict):
                continue
            url = str(result.get("url") or result.get("link") or "")
            key = _url_key(url)
            host = _host(url)
            if not key or host == own_host or key in seen:
                continue
            seen.add(key)
            selected.append(url)
            if len(selected) >= limit:
                break
        return selected

    def fetch_page(self, url: str) -> str:
        """Lit une page via le cache/extracteur fourni par l'adaptateur."""

        try:
            text = self.fetch_fn(url) or ""
        except Exception as exc:
            self.fetch_errors.append(f"{url}: {exc}")
            return ""
        if text.strip():
            self.pages_read += 1
        else:
            self.fetch_errors.append(f"{url}: contenu vide")
        return text

    def stats(self) -> dict[str, object]:
        return {
            "searches": self.searches,
            "pages_read": self.pages_read,
            "search_errors": list(self.search_errors),
            "fetch_errors": list(self.fetch_errors),
        }


def from_ideas_studio(project_id: str | None = None) -> ExistingPipelineWebAdapter:
    """Construit l'adaptateur avec les services existants, sans les modifier."""

    from app.services.seo.adapters.serp_adapter import get_serp_adapter
    from app.services.seo.agent_writer_openrouter import page_fetcher

    serp = get_serp_adapter(project_id)
    return ExistingPipelineWebAdapter(
        search_fn=serp.search,
        fetch_fn=page_fetcher(),
    )
