from __future__ import annotations


class SerpAdapter:
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
        if getattr(settings, "SERP_API_KEY", None):
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = "configured"

    def search(self, query: str, limit: int = 10) -> list[dict]:
        if not self.configured:
            return []
        try:
            import httpx
            api_key = __import__("app.core.config", fromlist=["settings"]).settings.SERP_API_KEY
            resp = httpx.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": api_key, "num": limit},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("organic_results", [])[:limit]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })
            if results:
                self.real_data_available = True
            return results
        except Exception as exc:
            self.last_error = str(exc)
            self.real_data_available = False
            return []

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
