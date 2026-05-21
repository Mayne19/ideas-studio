from __future__ import annotations


class ImageSourcingAdapter:
    provider_name = "image_sourcing"
    enabled = False
    configured = False
    requires_api_key = True
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "none"

    def __init__(self):
        from app.core.config import settings
        if getattr(settings, "UNSPLASH_ACCESS_KEY", None):
            self.configured = True
            self.enabled = True
            self.fallback_mode = "unsplash"

    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not self.configured:
            return []
        try:
            import httpx
            key = __import__("app.core.config", fromlist=["settings"]).settings.UNSPLASH_ACCESS_KEY
            resp = httpx.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": limit},
                headers={"Authorization": f"Client-ID {key}"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("results", [])[:limit]:
                results.append({
                    "image_url": item["urls"]["regular"],
                    "source_url": item["links"]["html"],
                    "source_name": "Unsplash",
                    "author": item["user"]["name"],
                    "license": "Unsplash License",
                    "alt_text": item.get("alt_description", ""),
                    "caption": "",
                    "usage_rights_status": "free_with_attribution",
                })
            if results:
                self.real_data_available = True
            return results
        except Exception as exc:
            self.last_error = str(exc)
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


image_sourcing_adapter = ImageSourcingAdapter()
