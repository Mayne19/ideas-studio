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


def _text(block) -> str:
    return getattr(block, "text", None) or (block.get("text") if isinstance(block, dict) else "") or ""


class OpenRouterAgentClient:
    def __init__(self, api_key: str, *, search_fn: Callable[[str, int], list[dict]],
                 fetch_fn: Callable[[str], str], model: str = OPENROUTER_AGENT_MODEL,
                 max_searches: int = 10, max_fetches: int = 15, post: Callable | None = None,
                 timeout_seconds: float = 600.0, max_cost_usd: float = MAX_COST_USD):
        self.api_key = api_key
        self.model = model
        self.search_fn = search_fn
        self.fetch_fn = fetch_fn
        self.max_searches = max_searches
        self.max_fetches = max_fetches
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
            results = self.search_fn(str(args.get("query") or ""), 10) or []
            return json.dumps([{"title": r.get("title", ""), "url": r.get("url") or r.get("link", ""),
                                "snippet": r.get("snippet", "")} for r in results], ensure_ascii=False)
        if name == "web_fetch":
            if self.fetches >= self.max_fetches:
                return "Limite de pages lues atteinte : rédige avec ce que tu as déjà."
            self.fetches += 1
            url = str(args.get("url") or "")
            text = self.fetch_fn(url) or ""
            if not text.strip():
                return (f"ÉCHEC DE LECTURE : la page {url} est vide, bloquée ou illisible. "
                        "Choisis une autre page (autre concurrent ou autre source).")
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
                                          server_tool_use=SimpleNamespace(web_search_requests=self.searches,
                                                                          web_fetch_requests=self.fetches)),
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


def page_fetcher(cache=None) -> Callable[[str], str]:
    """Lecture d'une page avec le cache et l'extracteur du pipeline."""
    from app.services.seo.adapters.content_extraction_adapter import content_extraction_adapter
    from app.services.seo.page_cache import PageCache

    cache = cache or PageCache()

    def fetch(url: str) -> str:
        html = cache.get_html(url)
        if not html:
            return ""
        extracted = content_extraction_adapter.extract_from_html(html, url) or {}
        return extracted.get("text") or ""
    return fetch
