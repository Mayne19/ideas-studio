from __future__ import annotations


class TrendsAdapter:
    provider_name = "google_trends"
    enabled = False
    configured = False
    requires_api_key = False
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "none"

    def __init__(self):
        pass

    def get_trends(self, keyword: str) -> dict:
        return {
            "status": "not_configured",
            "keyword": keyword,
            "trend_score": None,
            "rising_queries": [],
            "related_topics": [],
        }

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


trends_adapter = TrendsAdapter()
