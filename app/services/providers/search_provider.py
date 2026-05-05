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

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class MockSearchProvider(SearchProvider):
    """Always available; returns template-based results for dev and tests."""
    is_mock: bool = True

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

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        try:
            import httpx
            params = {"q": query, "format": "json", "number_of_results": limit}
            resp = httpx.get(f"{self.base_url}/search", params=params, timeout=15)
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
            httpx.get(f"{self.base_url}/search", params={"q": "test", "format": "json"}, timeout=5)
            return True
        except Exception:
            return False


def get_search_provider() -> SearchProvider:
    from app.core.config import settings
    if settings.DEFAULT_SEARCH_PROVIDER == "searxng" and settings.SEARXNG_URL:
        provider = SearXNGSearchProvider(settings.SEARXNG_URL)
        if provider.is_available():
            return provider
    return MockSearchProvider()
