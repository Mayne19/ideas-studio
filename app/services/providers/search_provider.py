import json
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider(ABC):
    is_mock: bool = False
    provider_name: str = "unknown"

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    def describe(self) -> str:
        return f"{self.provider_name} mock={self.is_mock}"


class MockSearchProvider(SearchProvider):
    """Always available; returns template-based results for dev and tests."""
    is_mock: bool = True
    provider_name: str = "mock"

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"[Mock] Guide complet sur {query}",
                url=f"https://example.com/guide-{query.replace(' ', '-').lower()}",
                snippet=f"Découvrez tout ce qu'il faut savoir sur {query}. Conseils pratiques et exemples concrets.",
            ),
            SearchResult(
                title=f"[Mock] {query} : les meilleures pratiques",
                url=f"https://example.com/meilleures-pratiques-{query.replace(' ', '-').lower()}",
                snippet=f"Les experts partagent leurs conseils sur {query} pour obtenir les meilleurs résultats.",
            ),
        ][:limit]

    def is_available(self) -> bool:
        return True


class SearXNGSearchProvider(SearchProvider):
    """Uses a local SearXNG instance for web search."""
    is_mock: bool = False
    provider_name: str = "searxng"

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        try:
            import httpx
            from app.core.config import settings
            fmt = settings.SEARXNG_FORMAT or "json"
            params = {"q": query, "format": fmt, "number_of_results": limit}
            resp = httpx.get(f"{self.base_url}/search", params=params, timeout=settings.SEARCH_TIMEOUT_SECONDS or 30)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("results", [])[:limit]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                ))
            return results
        except Exception:
            return []

    def is_available(self) -> bool:
        try:
            import httpx
            from app.core.config import settings
            fmt = settings.SEARXNG_FORMAT or "json"
            httpx.get(f"{self.base_url}/search", params={"q": "test", "format": fmt}, timeout=5)
            return True
        except Exception:
            return False


class BraveSearchProvider(SearchProvider):
    """Brave Search API — indépendant de l'index Google, ne nécessite ni
    projet Google Cloud ni moteur de recherche personnalisé. Facturation à
    l'usage (~0.003-0.005$/requête), crédit mensuel offert à l'inscription.
    Voir https://api-dashboard.search.brave.com/."""
    is_mock: bool = False
    provider_name: str = "brave_search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        try:
            import httpx
            from app.core.config import settings
            resp = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": min(limit, 20)},
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
            )
            resp.raise_for_status()
            data = resp.json()
            results = (data.get("web") or {}).get("results", [])
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                )
                for item in results[:limit]
            ]
        except Exception:
            return []

    def is_available(self) -> bool:
        return bool(self.api_key)


class GoogleCustomSearchProvider(SearchProvider):
    """Google Custom Search JSON API — nécessite une clé API + un moteur de
    recherche personnalisé (cx) configuré sur https://programmablesearchengine.google.com/.
    Limite gratuite : 100 requêtes/jour, 10 résultats max par appel."""
    is_mock: bool = False
    provider_name: str = "google_custom_search"

    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        try:
            import httpx
            from app.core.config import settings
            resp = httpx.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"key": self.api_key, "cx": self.cx, "q": query, "num": min(limit, 10)},
                timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
            )
            resp.raise_for_status()
            data = resp.json()
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                )
                for item in data.get("items", [])[:limit]
            ]
        except Exception:
            return []

    def is_available(self) -> bool:
        return bool(self.api_key and self.cx)


def get_search_provider() -> SearchProvider:
    from app.core.config import settings

    if settings.DEFAULT_SEARCH_PROVIDER == "searxng" and settings.SEARXNG_URL:
        provider = SearXNGSearchProvider(settings.SEARXNG_URL)
        if provider.is_available():
            return provider

    if settings.DEFAULT_SEARCH_PROVIDER == "brave" and settings.BRAVE_SEARCH_API_KEY:
        provider = BraveSearchProvider(settings.BRAVE_SEARCH_API_KEY)
        if provider.is_available():
            return provider

    if settings.DEFAULT_SEARCH_PROVIDER == "google" and settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_CX:
        provider = GoogleCustomSearchProvider(settings.GOOGLE_SEARCH_API_KEY, settings.GOOGLE_SEARCH_CX)
        if provider.is_available():
            return provider

    # "auto" et repli : utiliser le premier provider réel réellement configuré,
    # peu importe DEFAULT_SEARCH_PROVIDER — évite de tourner sur des données
    # inventées (MockSearchProvider) simplement parce que la variable
    # d'environnement n'a pas été mise à jour après l'ajout d'une clé. Brave
    # est essayé avant Google : les nouveaux moteurs de recherche personnalisés
    # Google (cx) ne peuvent plus interroger le web entier (fonctionnalité
    # dépréciée côté Google, cause d'un 403 permanent quoi que la config
    # fasse), Brave n'a pas cette limitation.
    if settings.BRAVE_SEARCH_API_KEY:
        provider = BraveSearchProvider(settings.BRAVE_SEARCH_API_KEY)
        if provider.is_available():
            return provider
    if settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_CX:
        provider = GoogleCustomSearchProvider(settings.GOOGLE_SEARCH_API_KEY, settings.GOOGLE_SEARCH_CX)
        if provider.is_available():
            return provider
    if settings.SEARXNG_URL:
        provider = SearXNGSearchProvider(settings.SEARXNG_URL)
        if provider.is_available():
            return provider

    return MockSearchProvider()
