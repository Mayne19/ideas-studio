from __future__ import annotations

"""Détection de tendances — approximation via Google Custom Search, pas de
vraie API Google Trends gratuite disponible. Compare le volume de résultats
récents (dernier mois) à un an de recul pour un même mot-clé : un ratio
nettement supérieur à 1 suggère un sujet en hausse d'intérêt, sans être une
mesure de volume de recherche réelle (juste un proxy indirect basé sur
combien de pages web récentes en parlent)."""


class TrendsAdapter:
    provider_name = "google_trends_proxy"
    enabled = False
    configured = False
    requires_api_key = True
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "low"  # proxy indirect, jamais présenté comme une vraie mesure Google Trends

    def __init__(self):
        from app.core.config import settings
        if settings.GOOGLE_SEARCH_API_KEY and settings.GOOGLE_SEARCH_CX:
            self.configured = True
            self.enabled = True
            self.fallback_mode = "google_custom_search_proxy"

    def get_trends(self, keyword: str) -> dict:
        if not self.configured:
            return {
                "status": "not_configured",
                "keyword": keyword,
                "trend_score": None,
                "rising_queries": [],
                "related_topics": [],
            }
        try:
            recent_count = self._result_count(keyword, date_restrict="m1")
            yearly_count = self._result_count(keyword, date_restrict="y1")
            if yearly_count == 0:
                trend_score = None
                status = "insufficient_data"
            else:
                # Ratio résultats récents (1 mois, extrapolé sur 12) vs total annuel —
                # >1 suggère une hausse d'activité, <1 une baisse, ~1 stable.
                trend_score = round((recent_count * 12) / yearly_count, 2) if yearly_count else None
                status = "success"
            self.real_data_available = True
            return {
                "status": status,
                "keyword": keyword,
                "trend_score": trend_score,
                "recent_results": recent_count,
                "yearly_results": yearly_count,
                "rising_queries": [],
                "related_topics": [],
                "method": "google_custom_search_volume_proxy",
            }
        except Exception as exc:
            self.last_error = str(exc)
            self.real_data_available = False
            return {
                "status": "error",
                "keyword": keyword,
                "trend_score": None,
                "rising_queries": [],
                "related_topics": [],
                "message": str(exc),
            }

    def _result_count(self, keyword: str, date_restrict: str) -> int:
        import httpx
        from app.core.config import settings
        resp = httpx.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": settings.GOOGLE_SEARCH_API_KEY,
                "cx": settings.GOOGLE_SEARCH_CX,
                "q": keyword,
                "dateRestrict": date_restrict,
                "num": 1,
            },
            timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
        )
        resp.raise_for_status()
        data = resp.json()
        return int(data.get("searchInformation", {}).get("totalResults", 0) or 0)

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
