from __future__ import annotations


class SerpAdapter:
    """Analyse concurrentielle SERP — SerpAPI (SERP_API_KEY) en priorité si
    configurée, sinon repli sur Google Custom Search (GOOGLE_SEARCH_API_KEY/
    GOOGLE_SEARCH_CX, déjà utilisé pour la génération d'idées) plutôt que de
    rester inactif faute d'une deuxième clé séparée."""
    provider_name = "serp"
    enabled = False
    configured = False
    requires_api_key = True
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "none"

    def __init__(self):
        from app.core.config import settings
        if settings.SERP_API_KEY:
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = "serpapi"
        elif settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_CX:
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = "google_custom_search"

    def search(self, query: str, limit: int = 10) -> list[dict]:
        if not self.configured:
            return []
        from app.core.config import settings
        try:
            if settings.SERP_API_KEY:
                return self._search_serpapi(query, limit)
            return self._search_google(query, limit)
        except Exception as exc:
            self.last_error = str(exc)
            self.real_data_available = False
            return []

    def _search_serpapi(self, query: str, limit: int) -> list[dict]:
        import httpx
        from app.core.config import settings
        resp = httpx.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": settings.SERP_API_KEY, "num": limit},
            timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [
            {"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")}
            for item in data.get("organic_results", [])[:limit]
        ]
        if results:
            self.real_data_available = True
        return results

    def _search_google(self, query: str, limit: int) -> list[dict]:
        import httpx
        from app.core.config import settings
        resp = httpx.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": settings.GOOGLE_SEARCH_API_KEY,
                "cx": settings.GOOGLE_SEARCH_CX,
                "q": query,
                "num": min(limit, 10),
            },
            timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [
            {"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")}
            for item in data.get("items", [])[:limit]
        ]
        if results:
            self.real_data_available = True
        return results

    def get_status(self) -> dict:
        return {
            "provider_name": self.provider_name,
            "enabled": self.enabled,
            "configured": self.configured,
            "requires_api_key": self.requires_api_key,
            "last_error": self.last_error,
            "real_data_available": self.real_data_available,
            "fallback_mode": self.fallback_mode,
            "trust_level": self.trust_level,
        }


serp_adapter = SerpAdapter()
