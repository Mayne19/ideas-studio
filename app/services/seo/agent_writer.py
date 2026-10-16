"""Agent rédacteur unique (mode de génération « agent »).

Un seul modèle fort (Claude Opus 5.5 par défaut, réglable dans Paramètres →
Agents, agent « agent_writer ») fait la recherche, la lecture des
concurrents et des sources, le plan, la rédaction et la relecture, avec les
outils serveur web_search et web_fetch d'Anthropic et le prompt système de
docs/AGENT-WRITER-PROMPT.md. Le code d'Ideas Studio garde le reste :
contexte du site, cannibalisation, contrôles (structure, plagiat,
cohérence, assemblage), données structurées et publication.

Spécification : « Agent rédacteur Ideas Studio : spécification complète »
(2026-10-17). Le client Anthropic est injecté (testable avec un faux client).
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from time import perf_counter
from typing import Any

from app.services.seo.html_text_ops import extract_json_object

logger = logging.getLogger(__name__)

DEFAULT_AGENT_MODEL = "claude-opus-5-5"
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 10}
WEB_FETCH_TOOL = {"type": "web_fetch_20260318", "name": "web_fetch", "max_uses": 15}
MAX_OUTPUT_TOKENS = 32000
MAX_PAUSE_CONTINUATIONS = 8
MAX_CORRECTION_ROUNDS = 2
REQUIRED_KEYS = ("title", "meta_title", "meta_description", "slug", "content_html", "faq")
PROMPT_PATH = Path(__file__).resolve().parents[3] / "docs" / "AGENT-WRITER-PROMPT.md"

LANGUAGE_NAMES = {"fr": "français", "en": "anglais", "de": "allemand", "es": "espagnol", "it": "italien",
                  "nl": "néerlandais", "pt": "portugais"}
COUNTRY_NAMES = {"FR": "France", "BE": "Belgique", "CH": "Suisse", "CA": "Canada", "GB": "Royaume-Uni",
                 "US": "États-Unis", "DE": "Allemagne", "ES": "Espagne", "IT": "Italie", "NL": "Pays-Bas"}

CORRECTION_INSTRUCTION = "Corrige uniquement ces points, renvoie le JSON complet."


class AgentWriterError(RuntimeError):
    pass


def load_system_prompt(*, site_name: str, site_domain: str, langue: str, pays: str,
                       today: date | None = None, template: str | None = None) -> str:
    """Prompt système de docs/AGENT-WRITER-PROMPT.md, variables remplacées.
    Remplacement ciblé (pas str.format : le prompt contient des accolades JSON)."""
    text = template if template is not None else PROMPT_PATH.read_text(encoding="utf-8")
    values = {
        "{site_name}": site_name or "le site",
        "{site_domain}": site_domain or "ce site",
        "{langue}": langue,
        "{pays}": pays,
        "{date}": (today or date.today()).isoformat(),
    }
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def locale_names(locale: str | None) -> tuple[str, str]:
    """« fr-FR » -> (« français », « France »)."""
    lang, _, country = (locale or "fr-FR").partition("-")
    return LANGUAGE_NAMES.get(lang.lower(), lang), COUNTRY_NAMES.get((country or "FR").upper(), country or "France")


def build_user_message(*, keyword: str, category: str | None = None, editor_notes: str | None = None,
                       published_articles: list[dict] | None = None) -> str:
    lines = [f"Mot-clé : {keyword}"]
    if category:
        lines.append(f"Catégorie : {category}")
    if editor_notes:
        lines.append(f"Consignes de l'éditeur : {editor_notes}")
    published = [a for a in published_articles or [] if a.get("url") and a.get("title")]
    if published:
        lines.append("Articles déjà publiés sur le site (pour les liens internes, n'invente aucune autre URL) :")
        lines += [f"- {a['title']} : {a['url']}" for a in published[:60]]
    else:
        lines.append("Aucun article publié sur le site pour l'instant : pas de lien interne.")
    return "\n".join(lines)


def _text_of(content: list) -> str:
    return "".join(getattr(block, "text", "") or "" for block in content if getattr(block, "type", "") == "text")


def _usage_add(total: dict, usage: Any) -> None:
    if usage is None:
        return
    total["input_tokens"] += int(getattr(usage, "input_tokens", 0) or 0)
    total["output_tokens"] += int(getattr(usage, "output_tokens", 0) or 0)
    total["cache_read_input_tokens"] += int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    server = getattr(usage, "server_tool_use", None)
    if server is not None:
        total["web_searches"] += int(getattr(server, "web_search_requests", 0) or 0)
        total["web_fetches"] += int(getattr(server, "web_fetch_requests", 0) or 0)


def _count_tool_blocks(content: list, total: dict) -> None:
    """Repli si l'usage ne détaille pas les outils serveur."""
    for block in content:
        if getattr(block, "type", "") == "server_tool_use":
            name = getattr(block, "name", "")
            key = "_counted_searches" if name == "web_search" else "_counted_fetches" if name == "web_fetch" else None
            if key:
                total[key] = total.get(key, 0) + 1


def validate_output(data: Any) -> list[str]:
    """Problèmes du JSON rendu par l'agent (clés manquantes, contenu vide)."""
    if not isinstance(data, dict):
        return ["réponse non JSON"]
    problems = [f"clé manquante : {k}" for k in REQUIRED_KEYS if not data.get(k)]
    if isinstance(data.get("content_html"), str) and len(data["content_html"].split()) < 150:
        problems.append("content_html trop court")
    if data.get("faq") is not None and not isinstance(data.get("faq"), list):
        problems.append("faq doit être une liste")
    return problems


class AgentWriter:
    """Une conversation avec l'agent : rédaction, puis corrections dans la
    même conversation (le contexte des recherches reste disponible)."""

    def __init__(self, client: Any, *, model: str = DEFAULT_AGENT_MODEL, system: str,
                 tools: list[dict] | None = None, max_tokens: int = MAX_OUTPUT_TOKENS):
        self.client = client
        self.model = model
        self.system = system
        self.tools = tools if tools is not None else [WEB_SEARCH_TOOL, WEB_FETCH_TOOL]
        self.max_tokens = max_tokens
        self.messages: list[dict] = []
        self.usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                      "web_searches": 0, "web_fetches": 0, "calls": 0}
        self.started = perf_counter()

    def _call(self):
        self.usage["calls"] += 1
        kwargs = {"model": self.model, "max_tokens": self.max_tokens, "system": self.system,
                  "messages": self.messages, "tools": self.tools}
        stream = getattr(self.client.messages, "stream", None)
        if stream is not None:
            # Streaming : les longues générations (recherches + article) dépassent
            # sinon la limite de durée des requêtes non streamées du SDK.
            with stream(**kwargs) as s:
                return s.get_final_message()
        return self.client.messages.create(**kwargs)

    def _run_turn(self) -> str:
        """Boucle jusqu'à la réponse finale : « pause_turn » (outils serveur
        longs) est relancé avec le contenu déjà produit."""
        for _ in range(MAX_PAUSE_CONTINUATIONS + 1):
            response = self._call()
            _usage_add(self.usage, getattr(response, "usage", None))
            _count_tool_blocks(response.content, self.usage)
            self.messages.append({"role": "assistant", "content": response.content})
            if getattr(response, "stop_reason", "") != "pause_turn":
                if getattr(response, "stop_reason", "") == "max_tokens":
                    raise AgentWriterError("réponse tronquée (limite de jetons atteinte)")
                return _text_of(response.content)
        raise AgentWriterError("trop de reprises de tour (pause_turn)")

    def _parse(self, text: str) -> tuple[dict | None, list[str]]:
        data = extract_json_object(text)
        return data, validate_output(data)

    def write(self, user_message: str, json_retries: int = 1) -> dict:
        self.messages.append({"role": "user", "content": user_message})
        data, problems = self._parse(self._run_turn())
        for _ in range(json_retries):
            if not problems:
                break
            self.messages.append({"role": "user", "content": (
                "Ta réponse n'est pas un JSON valide conforme au format demandé (" + "; ".join(problems)
                + "). Renvoie uniquement le JSON complet.")})
            data, problems = self._parse(self._run_turn())
        if problems:
            raise AgentWriterError("JSON invalide : " + "; ".join(problems))
        return data

    def correct(self, errors: list[str]) -> dict | None:
        """Un tour de correction dans la même conversation ; None si la
        réponse corrigée est inexploitable."""
        self.messages.append({"role": "user", "content": CORRECTION_INSTRUCTION + "\n"
                              + "\n".join(f"- {e}" for e in errors)})
        data, problems = self._parse(self._run_turn())
        return None if problems else data

    def report(self) -> dict:
        searches = self.usage["web_searches"] or self.usage.get("_counted_searches", 0)
        fetches = self.usage["web_fetches"] or self.usage.get("_counted_fetches", 0)
        from app.services.cost_estimator import estimate_agent_writer_cost
        return {
            "model": self.model,
            "duration_s": round(perf_counter() - self.started, 1),
            "calls": self.usage["calls"],
            "input_tokens": self.usage["input_tokens"],
            "output_tokens": self.usage["output_tokens"],
            "cache_read_input_tokens": self.usage["cache_read_input_tokens"],
            "web_searches": searches,
            "web_fetches": fetches,
            "cost_usd": estimate_agent_writer_cost(self.model, self.usage["input_tokens"],
                                                   self.usage["output_tokens"], searches),
        }


def anthropic_client(api_key: str, timeout_seconds: float = 900.0):
    import anthropic
    return anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds)


def resolve_agent_credentials(db, project_id: str | None) -> tuple[str | None, str]:
    """(clé Anthropic, modèle) depuis le CMS : clé du fournisseur
    « anthropic » (projet puis globale), modèle de l'agent « agent_writer »
    s'il est assigné, sinon celui de la clé, sinon DEFAULT_AGENT_MODEL."""
    from sqlalchemy import select

    from app.core.security import decrypt_secret
    from app.models.ai import Agent, AgentBinding, Provider, ProviderCredential

    provider = db.execute(select(Provider).where(Provider.code == "anthropic")).scalar_one_or_none()
    if provider is None:
        return None, DEFAULT_AGENT_MODEL
    credential = None
    for pid in ([project_id] if project_id else []) + [None]:
        query = select(ProviderCredential).where(ProviderCredential.provider_id == provider.id)
        query = query.where(ProviderCredential.project_id == pid) if pid else query.where(ProviderCredential.project_id.is_(None))
        credential = db.execute(query).scalar_one_or_none()
        if credential is not None:
            break
    model = DEFAULT_AGENT_MODEL
    agent = db.execute(select(Agent).where(Agent.key == "agent_writer")).scalar_one_or_none()
    if agent is not None:
        for pid in ([project_id] if project_id else []) + [None]:
            query = select(AgentBinding).where(AgentBinding.agent_id == agent.id, AgentBinding.is_enabled.is_(True))
            query = query.where(AgentBinding.project_id == pid) if pid else query.where(AgentBinding.project_id.is_(None))
            binding = db.execute(query).scalars().first()
            if binding is not None and binding.model:
                model = binding.model
                break
    if model == DEFAULT_AGENT_MODEL and credential is not None and credential.model and "opus" in credential.model:
        model = credential.model
    api_key = decrypt_secret(credential.secret_ref) if credential is not None else None
    return api_key or None, model


def dumps_safe(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)
