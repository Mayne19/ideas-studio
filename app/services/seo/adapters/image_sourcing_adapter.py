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

    def __init__(self, credential=None):
        """credential : ServiceCredential "brand_images" (voir
        app/services/providers/external_services.py) ; absent = repli env
        (BRAVE_SEARCH_API_KEY). Voir get_brave_image_search_provider()."""
        if credential is None:
            from app.services.providers.external_services import env_credential
            credential = env_credential("brand_images")
        self.api_key = credential.api_key if credential is not None else None
        self.source = credential.source if credential is not None else None
        if self.api_key:
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
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
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
            "credential_source": self.source,
        }


def get_brave_image_search_provider(project_id: str | None = None) -> BraveImageSearchProvider:
    """Config CMS (images officielles, sinon clé Brave de la recherche web ;
    projet puis global), puis env. project_id absent : celui du job courant."""
    from app.services.providers.external_services import resolve_credential

    return BraveImageSearchProvider(resolve_credential("brand_images", project_id))


# Compat : singleton env uniquement, préférer get_brave_image_search_provider().
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

    def __init__(self, credential=None):
        """credential : ServiceCredential "images" (voir
        app/services/providers/external_services.py) ; absent = repli env
        (UNSPLASH_ACCESS_KEY). Voir get_image_sourcing_adapter()."""
        if credential is None:
            from app.services.providers.external_services import env_credential
            credential = env_credential("images")
        self.api_key = credential.api_key if credential is not None and credential.provider == "unsplash" else None
        self.source = credential.source if self.api_key else None
        if self.api_key:
            self.configured = True
            self.enabled = True
            self.fallback_mode = "unsplash"

    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not self.configured:
            return []
        try:
            import httpx
            from app.core.config import settings
            key = self.api_key
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
                user = item.get("user") or {}
                links = item.get("links") or {}
                results.append({
                    "image_url": item["urls"]["regular"],
                    "source_url": links.get("html", ""),
                    "source_name": "Unsplash",
                    "author": user.get("name"),
                    # Profil du photographe : lien d'attribution obligatoire
                    # (Unsplash API Guidelines), complété des paramètres UTM
                    # au rendu (image_plan_service._image_html).
                    "author_url": (user.get("links") or {}).get("html"),
                    # À appeler quand la photo est réellement utilisée
                    # (track_download) — exigence des Unsplash API Guidelines.
                    "download_location": links.get("download_location"),
                    "license": "Unsplash License",
                    # Description anglaise brute : indice pour rédiger l'alt
                    # localisé, jamais insérée telle quelle dans l'article.
                    "alt_text": item.get("alt_description") or "",
                    "caption": "",
                    "usage_rights_status": "free_with_attribution",
                })
            if results:
                self.real_data_available = True
            return results
        except Exception as exc:
            self.last_error = str(exc)
            return []

    def track_download(self, download_location: str | None) -> bool:
        """Signale à Unsplash qu'une photo est utilisée (endpoint
        download_location, Unsplash API Guidelines). Limité au domaine
        api.unsplash.com : l'URL vient d'une réponse API, jamais d'un tiers."""
        if not self.configured or not download_location:
            return False
        if not str(download_location).startswith("https://api.unsplash.com/"):
            return False
        try:
            import httpx
            from app.core.config import settings
            resp = httpx.get(
                download_location,
                headers={"Authorization": f"Client-ID {self.api_key}"},
                timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

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
            "credential_source": self.source,
        }


def get_image_sourcing_adapter(project_id: str | None = None) -> ImageSourcingAdapter:
    """Config CMS (projet puis global), puis env. project_id absent : celui
    de la requête/job en cours."""
    from app.services.providers.external_services import resolve_credential

    return ImageSourcingAdapter(resolve_credential("images", project_id))


# Compat : singleton env uniquement, préférer get_image_sourcing_adapter().
image_sourcing_adapter = ImageSourcingAdapter()
