from __future__ import annotations


def empty_serp_extras() -> dict:
    return {"people_also_ask": [], "related_searches": [], "answer_box": {}, "knowledge_graph": {}}


def _clip(value, limit: int = 600) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def parse_serper_extras(data: dict) -> dict:
    """Blocs annexes d'une réponse Serper, normalisés : questions « Autres
    questions posées » (avec l'extrait de réponse et sa source), recherches
    associées, encadré de réponse et knowledge graph."""
    extras = empty_serp_extras()
    if not isinstance(data, dict):
        return extras
    seen: set[str] = set()
    for item in data.get("peopleAlsoAsk") or []:
        if not isinstance(item, dict):
            continue
        question = _clip(item.get("question"), 200)
        if not question or question.lower() in seen:
            continue
        seen.add(question.lower())
        extras["people_also_ask"].append({
            "question": question,
            "snippet": _clip(item.get("snippet")),
            "title": _clip(item.get("title"), 200),
            "url": str(item.get("link") or ""),
        })
    for item in data.get("relatedSearches") or []:
        query = _clip(item.get("query") if isinstance(item, dict) else item, 150)
        if query and query not in extras["related_searches"]:
            extras["related_searches"].append(query)
    box = data.get("answerBox")
    if isinstance(box, dict) and box:
        extras["answer_box"] = {
            "title": _clip(box.get("title"), 200),
            "answer": _clip(box.get("answer")),
            "snippet": _clip(box.get("snippet")),
            "url": str(box.get("link") or ""),
        }
    graph = data.get("knowledgeGraph")
    if isinstance(graph, dict) and graph:
        attributes = graph.get("attributes") if isinstance(graph.get("attributes"), dict) else {}
        extras["knowledge_graph"] = {
            "title": _clip(graph.get("title"), 200),
            "type": _clip(graph.get("type"), 100),
            "description": _clip(graph.get("description")),
            "url": str(graph.get("descriptionLink") or graph.get("website") or ""),
            "attributes": {_clip(k, 80): _clip(v, 200) for k, v in list(attributes.items())[:12]},
        }
    return extras


_FALLBACK_MODES = {
    "serper": "serper",
    "serpapi": "serpapi",
    "brave": "brave_search",
    "google_cse": "google_custom_search",
}


class SerpAdapter:
    """Analyse concurrentielle SERP.

    La clé vient d'une ServiceCredential "search" (voir
    app/services/providers/external_services.py) : config projet du CMS,
    puis config globale, puis variables d'environnement. Utiliser
    get_serp_adapter(project_id) pour une résolution par projet ; un
    SerpAdapter() sans argument ne lit que l'environnement.

    Repli env : Serper (SERPER_API_KEY, vrais résultats Google) en priorité,
    puis SerpAPI (SERP_API_KEY), sinon Brave Search (BRAVE_SEARCH_API_KEY),
    sinon Google Custom Search (GOOGLE_SEARCH_API_KEY/GOOGLE_SEARCH_CX).
    Google est en dernier recours : les nouveaux moteurs de recherche
    personnalisés (cx) ne peuvent plus interroger le web entier
    (fonctionnalité dépréciée côté Google), donc un cx créé après cette
    dépréciation renvoie un 403 permanent quelle que soit la config du
    projet Google Cloud."""
    provider_name = "serp"
    enabled = False
    configured = False
    requires_api_key = True
    last_error: str | None = None
    real_data_available = False
    fallback_mode = "not_configured"
    trust_level = "none"

    def __init__(self, credential=None):
        self.last_extras = empty_serp_extras()
        if credential is None:
            from app.services.providers.external_services import env_credential
            credential = env_credential("search")
        if credential is not None and credential.provider == "google_cse" and not (credential.config or {}).get("cx"):
            credential = None
        self.credential = credential
        self.source = credential.source if credential is not None else None
        if credential is not None and credential.provider in _FALLBACK_MODES:
            self.configured = True
            self.enabled = True
            self.real_data_available = True
            self.fallback_mode = _FALLBACK_MODES[credential.provider]

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Résultats organiques seuls (compat). Les blocs annexes de la
        dernière requête Serper restent lisibles dans `last_extras`."""
        return self.search_full(query, limit)["organic"]

    def search_full(self, query: str, limit: int = 10) -> dict:
        """Réponse SERP complète : organic + peopleAlsoAsk, relatedSearches,
        answerBox et knowledgeGraph (Serper seulement ; les autres
        fournisseurs ne renvoient que les résultats organiques)."""
        self.last_extras = empty_serp_extras()
        if not self.configured:
            return {"organic": [], **empty_serp_extras()}
        try:
            provider = self.credential.provider
            if provider == "serper":
                organic = self._search_serper(query, limit)
            elif provider == "serpapi":
                organic = self._search_serpapi(query, limit)
            elif provider == "brave":
                organic = self._search_brave(query, limit)
            else:
                organic = self._search_google(query, limit)
        except Exception as exc:
            self.last_error = str(exc)
            self.real_data_available = False
            return {"organic": [], **empty_serp_extras()}
        return {"organic": organic, **self.last_extras}

    def _search_serper(self, query: str, limit: int) -> list[dict]:
        import httpx
        from app.core.config import settings
        resp = httpx.post(
            "https://google.serper.dev/search",
            json={"q": query, "num": min(limit, 20), "gl": "fr", "hl": "fr"},
            headers={"X-API-KEY": self.credential.api_key, "Content-Type": "application/json"},
            timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [
            {"title": item.get("title", ""), "url": item.get("link", ""), "snippet": item.get("snippet", "")}
            for item in data.get("organic", [])[:limit]
        ]
        self.last_extras = parse_serper_extras(data)
        if results:
            self.real_data_available = True
        return results

    def _search_brave(self, query: str, limit: int) -> list[dict]:
        import httpx
        from app.core.config import settings
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": min(limit, 20)},
            headers={"X-Subscription-Token": self.credential.api_key, "Accept": "application/json"},
            timeout=settings.SEARCH_TIMEOUT_SECONDS or 30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = [
            {"title": item.get("title", ""), "url": item.get("url", ""), "snippet": item.get("description", "")}
            for item in (data.get("web") or {}).get("results", [])[:limit]
        ]
        if results:
            self.real_data_available = True
        return results

    def _search_serpapi(self, query: str, limit: int) -> list[dict]:
        import httpx
        from app.core.config import settings
        resp = httpx.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": self.credential.api_key, "num": limit},
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
                "key": self.credential.api_key,
                "cx": self.credential.config.get("cx"),
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
            "credential_source": self.source,
        }


def get_serp_adapter(project_id: str | None = None) -> SerpAdapter:
    """Adaptateur résolu pour un projet (config CMS projet, puis globale,
    puis env). project_id absent : celui de la requête/job en cours."""
    from app.services.providers.external_services import resolve_db_credential

    credential = resolve_db_credential("search", project_id)
    if credential is not None:
        adapter = SerpAdapter(credential)
        if adapter.configured:
            return adapter
    return SerpAdapter()


# Compat : singleton construit à l'import, repli env uniquement. Les appelants
# qui connaissent le projet doivent préférer get_serp_adapter(project_id).
serp_adapter = SerpAdapter()
