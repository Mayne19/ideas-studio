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


class SerperSearchProvider(SearchProvider):
    """Serper.dev — résultats Google réels (organiques) via API. 2 500
    requêtes offertes à l'inscription, puis facturation à l'usage.
    Voir https://serper.dev/."""
    is_mock: bool = False
    provider_name: str = "serper"

    def __init__(self, api_key: str, gl: str = "fr", hl: str = "fr"):
        self.api_key = api_key
        self.gl = gl
        self.hl = hl

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        try:
            import httpx
            from app.core.config import settings
            resp = httpx.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": min(limit, 20), "gl": self.gl, "hl": self.hl},
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
            )
            resp.raise_for_status()
            results = resp.json().get("organic", [])
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
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


class SerpApiSearchProvider(SearchProvider):
    """SerpAPI — résultats Google via https://serpapi.com/."""
    is_mock: bool = False
    provider_name: str = "serpapi"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        try:
            import httpx
            from app.core.config import settings
            resp = httpx.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": self.api_key, "num": limit},
                timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
            )
            resp.raise_for_status()
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                )
                for item in resp.json().get("organic_results", [])[:limit]
            ]
        except Exception:
            return []

    def is_available(self) -> bool:
        return bool(self.api_key)


def build_search_provider(credential) -> SearchProvider | None:
    """SearchProvider réel à partir d'une ServiceCredential (voir
    app/services/providers/external_services.py), None si non supporté."""
    if credential is None or not credential.api_key:
        return None
    if credential.provider == "serper":
        return SerperSearchProvider(credential.api_key)
    if credential.provider == "brave":
        return BraveSearchProvider(credential.api_key)
    if credential.provider == "serpapi":
        return SerpApiSearchProvider(credential.api_key)
    if credential.provider == "google_cse":
        cx = (credential.config or {}).get("cx")
        return GoogleCustomSearchProvider(credential.api_key, cx) if cx else None
    return None


def get_search_provider(project_id: str | None = None) -> SearchProvider:
    """Clé configurée dans le CMS (projet, puis globale) en priorité — elle
    prime sur DEFAULT_SEARCH_PROVIDER — puis repli sur les variables
    d'environnement. project_id absent : celui de la requête/job en cours
    (current_project_id) est utilisé, voir resolve_db_credential."""
    from app.core.config import settings
    from app.services.providers.external_services import resolve_db_credential

    configured = build_search_provider(resolve_db_credential("search", project_id))
    if configured is not None and configured.is_available():
        return configured

    if settings.DEFAULT_SEARCH_PROVIDER == "searxng" and settings.SEARXNG_URL:
        provider = SearXNGSearchProvider(settings.SEARXNG_URL)
        if provider.is_available():
            return provider

    if settings.DEFAULT_SEARCH_PROVIDER == "serper" and settings.SERPER_API_KEY:
        provider = SerperSearchProvider(settings.SERPER_API_KEY)
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
    # fasse), Brave n'a pas cette limitation. Serper (vrais résultats Google)
    # passe en premier quand il est configuré.
    if settings.SERPER_API_KEY:
        provider = SerperSearchProvider(settings.SERPER_API_KEY)
        if provider.is_available():
            return provider
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
