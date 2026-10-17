"""Pont OpenRouter pour l'agent rédacteur unique.

Quand aucune clé Anthropic avec crédit n'est configurée, l'agent tourne sur
le même modèle via OpenRouter (« anthropic/claude-opus-5.5 »). OpenRouter
n'expose pas les outils serveur web_search et web_fetch d'Anthropic : ce
client les déclare comme outils classiques et les exécute lui-même
(recherche SERP du projet, lecture de page avec l'extracteur du pipeline).

Il imite l'interface utilisée par AgentWriter (client.messages.create) :
réponse avec `content` (blocs texte), `stop_reason` et `usage`
(server_tool_use : nombre de recherches et de pages lues). La conversation
complète (résultats d'outils compris) est gardée ici, pour que les tours de
correction voient les pages déjà lues.
"""
from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from typing import Callable

logger = logging.getLogger(__name__)

OPENROUTER_AGENT_MODEL = "anthropic/claude-opus-5.5"
MAX_TOOL_STEPS = 40
# Pages lues en entier ou presque (un concurrent de 3 000 mots ≈ 18 000
# caractères) : moins de pages, mais complètes (consigne du 2026-10-17).
PAGE_CHARS = 20_000
# En dessous, l'extraction a probablement raté le corps de la page (bannière,
# mur de cookies) : on tente le lecteur de secours, puis la lecture compte
# comme un échec (consigne du rédacteur en chef, 2026-10-17).
MIN_PAGE_CHARS = 1_500
AGENT_FETCH_TIMEOUT_SECONDS = 15.0
REASONING_EFFORT = "low"
MAX_COST_USD = 3.0


class AgentBudgetExceeded(RuntimeError):
    pass

TOOLS = [
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Recherche Google (résultats organiques : titre, URL, extrait).",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "web_fetch",
        "description": "Lit le texte principal d'une page web à partir de son URL.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    }},
]


def _url_key(url: str) -> str:
    """Clé de comparaison d'URL : sans schéma, « www. », ancre ni barre finale."""
    from urllib.parse import urlsplit

    try:
        parts = urlsplit((url or "").strip())
    except ValueError:
        return ""
    host = (parts.hostname or "").lower().removeprefix("www.")
    if not host:
        return ""
    return host + (parts.path.rstrip("/") or "/") + (f"?{parts.query}" if parts.query else "")


def _text(block) -> str:
    return getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else "") or ""


class OpenRouterAgentClient:
    def __init__(self, api_key: str, *, search_fn: Callable[[str, int], list[dict]],
                 fetch_fn: Callable[[str], str], model: str = OPENROUTER_AGENT_MODEL,
                 max_searches: int = 10, max_fetches: int = 15, post: Callable | None = None,
                 timeout_seconds: float = 600.0, max_cost_usd: float = MAX_COST_USD,
                 max_failed_fetches: int = 6):
        self.api_key = api_key
        self.model = model
        self.search_fn = search_fn
        self.fetch_fn = fetch_fn
        self.max_searches = max_searches
        self.max_fetches = max_fetches
        self.max_failed_fetches = max_failed_fetches
        self.failed_fetches = 0
        self.fetch_log: list[dict] = []
        self.search_log: list[str] = []
        self.seen_urls: set[str] = set()
        self.timeout_seconds = timeout_seconds
        self._post = post
        self.max_cost_usd = max_cost_usd
        self.cost_usd = 0.0
        self.reasoning_effort = REASONING_EFFORT
        self.transcript: list[dict] = []
        self.searches = 0
        self.fetches = 0
        self.messages = SimpleNamespace(create=self.create)

    def _http(self, payload: dict) -> dict:
        if self._post is not None:
            return self._post(payload)
        import httpx
        resp = httpx.post("https://openrouter.ai/api/v1/chat/completions", json=payload, timeout=self.timeout_seconds,
                          headers={"Authorization": f"Bearer {self.api_key}"})
        resp.raise_for_status()
        return resp.json()

    def _run_tool(self, name: str, args: dict) -> str:
        if name == "web_search":
            if self.searches >= self.max_searches:
                return "Limite de recherches atteinte : rédige avec ce que tu as déjà."
            self.searches += 1
            self.search_log.append(str(args.get("query") or ""))
            results = self.search_fn(str(args.get("query") or ""), 10) or []
            self.seen_urls |= {_url_key(r.get("url") or r.get("link") or "") for r in results} - {""}
            return json.dumps([{"title": r.get("title", ""), "url": r.get("url") or r.get("link", ""),
                                "snippet": r.get("snippet", "")} for r in results], ensure_ascii=False)
        if name == "web_fetch":
            if self.fetches >= self.max_fetches:
                return "Limite de pages lues atteinte : rédige avec ce que tu as déjà."
            if self.failed_fetches >= self.max_failed_fetches:
                return "Limite d'échecs de lecture atteinte : rédige avec ce que tu as déjà."
            url = str(args.get("url") or "")
            if _url_key(url) not in self.seen_urls:
                # URL devinée par le modèle (souvent une 404) : refusée sans
                # consommer le budget de lectures (consigne du 2026-10-17).
                self.fetch_log.append({"url": url, "chars": 0, "failed": True, "method": "refusée",
                                       "note": "URL absente des résultats de recherche"})
                return "URL inventée : choisis une URL issue d'une recherche."
            text = self.fetch_fn(url) or ""
            chars = len(text.strip())
            entry = {"url": url, "chars": chars} | dict(getattr(self.fetch_fn, "last", None) or {})
            if chars < MIN_PAGE_CHARS:
                # Une page illisible ou presque vide n'apporte rien : elle ne
                # consomme pas le budget de lectures, mais un plafond d'échecs.
                self.failed_fetches += 1
                self.fetch_log.append(entry | {"failed": True})
                return (f"ÉCHEC DE LECTURE ({chars} caractères) : la page {url} ne compte pas, "
                        "choisis une autre source.")
            self.fetches += 1
            self.fetch_log.append(entry | {"failed": False})
            return text[:PAGE_CHARS]
        return f"Outil inconnu : {name}"

    def _estimate(self, usage: dict) -> float:
        from app.services.cost_estimator import estimate_agent_writer_cost
        return estimate_agent_writer_cost(self.model, int(usage.get("prompt_tokens") or 0),
                                          int(usage.get("completion_tokens") or 0), 0)

    def create(self, *, model: str, max_tokens: int, system: str, messages: list[dict], tools=None, **_):
        if not self.transcript:
            self.transcript.append({"role": "system", "content": system})
        last = messages[-1]
        if last.get("role") == "user":
            content = last["content"] if isinstance(last["content"], str) else "".join(_text(b) for b in last["content"])
            self.transcript.append({"role": "user", "content": content})
        prompt_tokens = completion_tokens = 0
        # Compteurs de cet appel seulement (AgentWriter additionne les appels).
        searches_before, fetches_before = self.searches, self.fetches
        for _ in range(MAX_TOOL_STEPS):
            data = self._http({"model": self.model, "max_tokens": max_tokens, "messages": self.transcript,
                               # Claude Opus impose son raisonnement sur OpenRouter :
                               # effort réduit plutôt que désactivé (refusé).
                               "tools": TOOLS, "reasoning": {"effort": self.reasoning_effort}})
            usage = data.get("usage") or {}
            self.cost_usd += float(usage.get("cost") or 0.0) or self._estimate(usage)
            if self.cost_usd > self.max_cost_usd:
                raise AgentBudgetExceeded(
                    f"arrêt dur : coût cumulé {self.cost_usd:.2f} $ > {self.max_cost_usd:.2f} $")
            prompt_tokens += int(usage.get("prompt_tokens") or 0)
            completion_tokens += int(usage.get("completion_tokens") or 0)
            choice = data["choices"][0]
            message = choice["message"]
            calls = message.get("tool_calls") or []
            self.transcript.append({k: v for k, v in message.items() if k in ("role", "content", "tool_calls")})
            if not calls:
                stop = "max_tokens" if choice.get("finish_reason") == "length" else "end_turn"
                return SimpleNamespace(
                    content=[SimpleNamespace(type="text", text=message.get("content") or "")], stop_reason=stop,
                    usage=SimpleNamespace(input_tokens=prompt_tokens, output_tokens=completion_tokens,
                                          cache_read_input_tokens=0,
                                          server_tool_use=SimpleNamespace(
                                              web_search_requests=self.searches - searches_before,
                                              web_fetch_requests=self.fetches - fetches_before)),
                )
            for call in calls:
                try:
                    args = json.loads(call["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                try:
                    result = self._run_tool(call["function"]["name"], args)
                except Exception as exc:
                    result = f"Erreur de l'outil : {exc}"
                self.transcript.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        raise RuntimeError("trop d'étapes d'outils sans réponse finale")


READER_URL = "https://r.jina.ai/"
READER_TIMEOUT_SECONDS = 25.0


def reader_get(url: str, timeout: float = READER_TIMEOUT_SECONDS) -> tuple[str, int | None]:
    """Lecture de secours par un lecteur externe (page rendue puis convertie
    en texte) : utile pour les sites qui refusent les robots simples. Rend
    (texte, statut) ; une page d'erreur (4xx/5xx) donne un texte vide."""
    import httpx

    resp = httpx.get(READER_URL + url, timeout=timeout, headers={"Accept": "text/plain"})
    if resp.status_code >= 400:
        return "", resp.status_code
    text = resp.text
    if "Warning: Target URL returned error" in text[:1000]:
        return "", 404
    return text.split("Markdown Content:", 1)[-1].strip(), resp.status_code


def page_fetcher(cache=None, fallback: Callable[[str], tuple[str, int | None]] | None = reader_get
                 ) -> Callable[[str], str]:
    """Lecture d'une page avec le cache et l'extracteur du pipeline, puis le
    lecteur de secours si le texte extrait est trop court (robots.txt
    respecté). `fetch.last` décrit la dernière lecture pour le rapport."""
    from app.services.seo.adapters.content_extraction_adapter import content_extraction_adapter
    from app.services.seo.page_cache import PageCache

    cache = cache or PageCache()
    cache.timeout = max(cache.timeout, AGENT_FETCH_TIMEOUT_SECONDS)

    def fetch(url: str) -> str:
        html = cache.get_html(url)
        text = ""
        if html:
            text = (content_extraction_adapter.extract_from_html(html, url) or {}).get("text") or ""
        status = getattr(cache, "status", {}).get(cache._key(url)) if hasattr(cache, "_key") else None
        fetch.last = {"method": "directe", "status": status, "html_chars": len(html or ""),
                      "text_chars": len(text.strip())}
        if len(text.strip()) < MIN_PAGE_CHARS and fallback is not None and cache.allowed(url):
            try:
                rescued, rescue_status = fallback(url)
            except Exception as exc:  # réseau, délai : la lecture reste un échec
                logger.debug("lecteur de secours : échec %s : %s", url, exc)
                rescued, rescue_status = "", None
            fetch.last |= {"method": "secours", "status": rescue_status, "text_chars": len(rescued.strip())}
            if rescue_status == 429:
                fetch.last["note"] = "limite de débit du lecteur de secours atteinte"
            if len(rescued.strip()) > len(text.strip()):
                text = rescued
        return text
    fetch.last = {}
    return fetch
