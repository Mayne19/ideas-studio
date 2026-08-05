from __future__ import annotations


class BraveImageSearchProvider:
    """Recherche d'images restreinte à un domaine précis (site: officiel
    d'une marque/outil) via Brave Image Search — Unsplash ne référence que
    des photos génériques, pas les captures d'écran/logos publiés par une
    marque sur son propre site. Utilisé uniquement quand une section
    identifie un outil/marque nommé avec un domaine officiel connu."""
    provider_name = "brave_image_search"
    enabled = False
    configured = False
    requires_api_key = True
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "medium"  # dépend de la fiabilité du domaine ciblé, jamais garanti à 100%

    def __init__(self):
        from app.core.config import settings
        if settings.BRAVE_SEARCH_API_KEY:
            self.configured = True
            self.enabled = True
            self.fallback_mode = "brave_image_search"

    def search_on_domain(self, query: str, domain: str, limit: int = 3) -> list[dict]:
        if not self.configured:
            return []
        try:
            import httpx
            from app.core.config import settings
            resp = httpx.get(
                "https://api.search.brave.com/res/v1/images/search",
                params={"q": f"{query} site:{domain}", "count": min(limit, 20), "safesearch": "strict"},
                headers={"X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY, "Accept": "application/json"},
                timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in (data.get("results") or [])[:limit]:
                image_url = (item.get("properties") or {}).get("url") or item.get("thumbnail", {}).get("src")
                page_url = item.get("url") or ""
                if not image_url:
                    continue
                results.append({
                    "image_url": image_url,
                    "source_url": page_url,
                    "source_name": domain,
                    "author": None,
                    "license": "usage à vérifier — image officielle du site source",
                    "alt_text": item.get("title") or "",
                    "caption": "",
                    "usage_rights_status": "official_source",
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


brave_image_search_provider = BraveImageSearchProvider()


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
        if settings.UNSPLASH_ACCESS_KEY:
            self.configured = True
            self.enabled = True
            self.fallback_mode = "unsplash"

    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not self.configured:
            return []
        try:
            import httpx
            from app.core.config import settings
            key = settings.UNSPLASH_ACCESS_KEY
            resp = httpx.get(
                "https://api.unsplash.com/search/photos",
                params={"query": query, "per_page": limit},
                headers={"Authorization": f"Client-ID {key}"},
                timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
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
