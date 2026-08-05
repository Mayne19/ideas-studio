from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.providers.llm_provider import (
    LLMProvider,
    MockLLMProvider,
    ProviderUnavailableError,
)
from app.services.agents.agent_registry import get_agent, resolve_agent_id, agent_id_variants

logger = logging.getLogger(__name__)


class AgentProviderAssignmentError(ProviderUnavailableError):
    """Un provider est explicitement assigné à cet agent (AgentBinding) mais
    sa construction a échoué (clé indéchiffrable, config invalide...).

    Ne doit JAMAIS déclencher un repli silencieux vers le provider par
    défaut du projet ou global : l'utilisateur a choisi cette clé pour cet
    agent précis, un échec doit être visible et concret, pas masqué par une
    bascule vers une autre clé qu'il n'a pas choisie pour cet agent."""


@dataclass
class AgentCallResult:
    agent_id: str
    provider_name: str
    model_name: str | None = None
    duration_ms: int = 0
    tokens: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    actual_cost: float | None = None
    cost_status: str = "not_tracked"
    status: str = "success"
    error: str | None = None


class AgentRouter:
    """Routes LLM calls to the appropriate provider for each agent.

    Resolution order:
      1. AgentAssignment in DB (agent -> provider mapping), l'agent_id étant
         canonicalisé via le registre pour que les alias legacy retrouvent
         les assignations créées depuis l'UI (et inversement)
      2. Env var AGENT_{AGENT_ID}_PROVIDER (e.g. AGENT_CONTENT_WRITER_PROVIDER=openai)
      3. Provider par défaut du projet, puis global (get_llm_provider fallback)
    """

    def __init__(self, db: Session | None = None):
        self._db = db
        self._cache: dict[str, LLMProvider] = {}

    def get_provider(self, agent_id: str, project_id: str | None = None) -> LLMProvider:
        cache_key = f"{project_id or 'global'}:{agent_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        agent = get_agent(agent_id)
        if agent and not agent.requires_llm:
            provider = MockLLMProvider()
            self._cache[cache_key] = provider
            return provider

        from app.services.agents.agent_registry import AgentStatus
        if agent and agent.status == AgentStatus.not_implemented:
            provider = MockLLMProvider()
            self._cache[cache_key] = provider
            return provider

        provider = self._resolve_provider(agent_id, project_id)
        if provider is None:
            from app.services.providers.llm_provider import get_llm_provider
            provider = get_llm_provider()

        self._cache[cache_key] = provider
        return provider

    def _resolve_provider(self, agent_id: str, project_id: str | None = None) -> LLMProvider | None:
        canonical_id = resolve_agent_id(agent_id)
        # 1. DB assignment (ai.agent_bindings, résolu ligne projet sinon globale)
        if self._db is not None:
            try:
                from sqlalchemy import select
                from app.models.ai import Agent
                from app.services.providers.provider_config import (
                    resolve_binding_for_agent,
                    resolve_default_provider,
                )

                agent_row = self._db.execute(
                    select(Agent).where(Agent.key == canonical_id)
                ).scalar_one_or_none()
                if agent_row is not None:
                    config = resolve_binding_for_agent(self._db, agent_row.id, project_id)
                    if config is not None:
                        # Provider explicitement assigné à cet agent : un
                        # échec de construction ici ne doit jamais basculer
                        # silencieusement vers le défaut du projet ou global
                        # (voir AgentProviderAssignmentError) — c'est CETTE
                        # clé que l'utilisateur a choisie pour cet agent.
                        return self._build_provider(config, strict=True)

                if project_id is not None:
                    default_config = resolve_default_provider(self._db, project_id)
                    if default_config is not None:
                        return self._build_provider(default_config, strict=False)
            except AgentProviderAssignmentError:
                raise
            except Exception:
                logger.warning("AgentRouter: DB lookup failed for %s", agent_id, exc_info=True)

        # 2. Env var
        env_key = f"AGENT_{agent_id.upper()}_PROVIDER"
        provider_name = getattr(settings, env_key, None) or ""
        if provider_name:
            return self._build_from_env(provider_name, agent_id)

        return None

    def _build_provider(self, config, strict: bool = False) -> LLMProvider | None:
        from app.services.providers.llm_provider import build_provider_from_config

        try:
            provider = build_provider_from_config(config)
        except Exception as exc:
            if strict:
                raise AgentProviderAssignmentError(
                    f"Provider '{config.provider}' assigné à cet agent : construction impossible ({exc})."
                ) from exc
            logger.warning("AgentRouter: could not build provider %s: %s", config.provider, exc)
            return None
        if provider is None and strict:
            raise AgentProviderAssignmentError(
                f"Provider '{config.provider}' assigné à cet agent : clé API absente ou indéchiffrable."
            )
        return provider

    def _build_from_env(self, provider_name: str, agent_id: str) -> LLMProvider | None:
        from app.services.providers.llm_provider import get_llm_provider

        model_key = f"AGENT_{agent_id.upper()}_MODEL"
        model_override = getattr(settings, model_key, None) or ""

        try:
            provider = get_llm_provider()
            if not provider.is_mock and model_override:
                if hasattr(provider, "model_name") and model_override:
                    provider.model_name = model_override
                if hasattr(provider, "model") and model_override:
                    provider.model = model_override
            return provider
        except Exception:
            return None

    def clear_cache(self):
        self._cache.clear()


_default_router: AgentRouter | None = None


def get_agent_router(db: Session | None = None) -> AgentRouter:
    global _default_router
    if db is not None:
        return AgentRouter(db=db)
    if _default_router is None:
        _default_router = AgentRouter(db=db)
    return _default_router


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token."""
    return max(1, len(text) // 4)


def call_agent(
    agent_id: str,
    method: str,
    prompt: str,
    db: Session | None = None,
    project_id: str | None = None,
    article_id: str | None = None,
    system: str | None = None,
    temperature: float = 0.7,
    **kwargs,
) -> tuple[str, AgentCallResult]:
    """Call an agent and return (response_text, call_result)."""
    router = get_agent_router(db)
    start = time.perf_counter()
    error: str | None = None
    status = "success"
    response = ""

    try:
        provider = router.get_provider(agent_id, project_id=project_id)
    except ProviderUnavailableError as e:
        # Inclut AgentProviderAssignmentError : un agent avec un provider
        # explicitement assigné qui échoue à se construire (clé invalide...)
        # doit remonter comme status=error avec le message concret, jamais
        # comme une exception qui casse l'appelant — call_agent() retourne
        # toujours un tuple, jamais ne lève (pattern établi de ce module).
        duration_ms = int((time.perf_counter() - start) * 1000)
        result = AgentCallResult(
            agent_id=agent_id, provider_name="unknown", status="error", error=str(e),
            duration_ms=duration_ms,
        )
        return f"[Agent {agent_id} unavailable: {e}]", result

    try:
        if method == "generate_text":
            response = provider.generate_text(prompt, system=system, temperature=temperature, **kwargs)
        elif method == "generate_json":
            schema_hint = kwargs.get("schema_hint")
            result = provider.generate_json(prompt, schema_hint=schema_hint)
            import json
            response = json.dumps(result)
        else:
            raise ValueError(f"Unknown method: {method}")
    except ProviderUnavailableError as e:
        status = "error"
        error = str(e)
        response = f"[Agent {agent_id} unavailable: {e}]"
    except Exception as e:
        status = "error"
        error = str(e)
        response = f"[Agent {agent_id} error: {e}]"

    duration_ms = int((time.perf_counter() - start) * 1000)

    # Tokens réellement facturés si le provider les expose, sinon estimation (~4 car./token)
    reported_usage = getattr(provider, "last_usage", None)
    tokens_measured = isinstance(reported_usage, dict) and bool(reported_usage)
    if tokens_measured:
        input_tokens = int(reported_usage.get("input_tokens") or 0)
        output_tokens = int(reported_usage.get("output_tokens") or 0)
    else:
        input_tokens = _estimate_tokens(prompt)
        if system:
            input_tokens += _estimate_tokens(system)
        output_tokens = _estimate_tokens(response)

    estimated_cost: float | None = None
    actual_cost: float | None = None
    cost_status = "not_tracked"

    if status == "success":
        from app.services.cost_estimator import estimate_call_cost
        est = estimate_call_cost(
            provider=provider.provider_name,
            model=provider.model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        estimated_cost = est["estimated_cost_eur"]
        cost_status = est["cost_status"]
        if estimated_cost is not None:
            estimated_cost = round(estimated_cost, 6)
            # actual_cost n'est renseigné que sur des tokens réellement mesurés :
            # une estimation ne doit jamais être présentée comme un coût constaté.
            actual_cost = estimated_cost if tokens_measured else None
            if not tokens_measured and cost_status == "tracked":
                cost_status = "estimated"

    call_result = AgentCallResult(
        agent_id=agent_id,
        provider_name=provider.provider_name,
        model_name=provider.model_name,
        duration_ms=duration_ms,
        tokens=input_tokens + output_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=estimated_cost,
        actual_cost=actual_cost,
        cost_status=cost_status,
        status=status,
        error=error,
    )

    if db is not None:
        try:
            from app.models.ai import UsageEvent
            from app.models.reference import StepStatus, set_step_status
            log_entry = UsageEvent(
                agent_key=resolve_agent_id(agent_id),
                provider_code=provider.provider_name,
                model=provider.model_name,
                project_id=project_id,
                article_id=article_id,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                duration_ms=duration_ms,
                estimated_cost=estimated_cost,
                actual_cost=actual_cost,
                error_message=error if status != "success" else None,
            )
            set_step_status(log_entry, StepStatus.SUCCEEDED if status == "success" else StepStatus.FAILED)
            db.add(log_entry)
            db.commit()
        except Exception:
            logger.warning("Failed to log AI usage", exc_info=True)

    return response, call_result
