from __future__ import annotations


class GoogleWatchAdapter:
    provider_name = "google_watch"
    enabled = False
    configured = False
    requires_api_key = False
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "none"

    def __init__(self):
        self.enabled = True
        self.configured = True
        self.real_data_available = True
        self.trust_level = "medium"
        self.fallback_mode = "web_fetch"

    def fetch_status(self) -> list[dict]:
        updates = []
        sources = [
            ("https://status.search.google.com/", "Google Search Status Dashboard"),
            ("https://developers.google.com/search/", "Google Search Central"),
        ]
        for url, name in sources:
            try:
                import httpx
                resp = httpx.get(url, timeout=15)
                if resp.status_code == 200:
                    updates.append({
                        "source": name,
                        "url": url,
                        "status": "fetched",
                        "detected_at": __import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        ).isoformat(),
                    })
            except Exception:
                pass
        return updates if updates else [{"source": "google_watch", "status": "unavailable"}]

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


google_watch_adapter = GoogleWatchAdapter()
