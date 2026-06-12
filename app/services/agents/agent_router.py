from __future__ import annotations

import logging
import time
from typing import Protocol
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.providers.llm_provider import (
    LLMProvider,
    MockLLMProvider,
    ProviderUnavailableError,
)
from app.services.agents.agent_registry import get_agent

logger = logging.getLogger(__name__)


@dataclass
class AgentCallResult:
    agent_id: str
    provider_name: str
    model_name: str | None = None
    duration_ms: int = 0
    tokens: int = 0
    status: str = "success"
    error: str | None = None


class UsageLogger(Protocol):
    def log_call(
        self,
        db: Session,
        agent_id: str,
        provider_id: str | None,
        provider_name: str,
        model_name: str | None,
        project_id: str | None,
        article_id: str | None,
        duration_ms: int,
        status: str,
        error_message: str | None = None,
    ) -> None:
        ...


class AgentRouter:
    """Routes LLM calls to the appropriate provider for each agent.

    Resolution order:
      1. AgentAssignment in DB (agent -> provider mapping)
      2. Env var AGENT_{AGENT_ID}_PROVIDER (e.g. AGENT_CONTENT_WRITER_PROVIDER=openai)
      3. Global default provider (get_llm_provider fallback)
    """

    def __init__(self, db: Session | None = None, usage_logger: UsageLogger | None = None):
        self._db = db
        self._usage_logger = usage_logger
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

        provider = self._resolve_provider(agent_id, project_id)
        if provider is None:
            from app.services.providers.llm_provider import get_llm_provider
            provider = get_llm_provider()

        self._cache[cache_key] = provider
        return provider

    def _resolve_provider(self, agent_id: str, project_id: str | None = None) -> LLMProvider | None:
        # 1. DB assignment
        if self._db is not None:
            try:
                from app.models.agent_assignment import AgentAssignment
                from app.models.ai_provider_config import AIProviderConfig
                from app.core.security import decrypt_secret

                ass = (
                    self._db.query(AgentAssignment)
                    .filter(
                        AgentAssignment.project_id == project_id,
                        AgentAssignment.agent_id == agent_id,
                        AgentAssignment.enabled == True,
                    )
                    .first()
                )
                if ass is not None:
                    config = (
                        self._db.query(AIProviderConfig)
                        .filter(AIProviderConfig.id == ass.provider_id, AIProviderConfig.enabled == True)
                        .first()
                    )
                    if config is not None:
                        return self._build_provider(config)

                if project_id is not None:
                    default_config = (
                        self._db.query(AIProviderConfig)
                        .filter(
                            AIProviderConfig.project_id == project_id,
                            AIProviderConfig.is_default == True,
                            AIProviderConfig.enabled == True,
                        )
                        .first()
                    )
                    if default_config is not None:
                        return self._build_provider(default_config)
            except Exception:
                logger.warning("AgentRouter: DB lookup failed for %s", agent_id, exc_info=True)

        # 2. Env var
        env_key = f"AGENT_{agent_id.upper()}_PROVIDER"
        provider_name = getattr(settings, env_key, None) or ""
        if provider_name:
            return self._build_from_env(provider_name, agent_id)

        return None

    def _build_provider(self, config) -> LLMProvider | None:
        from app.core.security import decrypt_secret
        from app.services.providers.openai_provider import OpenAILLMProvider
        from app.services.providers.openrouter_provider import OpenRouterLLMProvider
        from app.services.providers.gemini_provider import GeminiLLMProvider
        from app.services.providers.llm_provider import OllamaLLMProvider

        api_key = decrypt_secret(config.api_key_encrypted)
        provider_name = config.provider

        try:
            if provider_name == "ollama":
                base_url = (config.base_url or settings.OLLAMA_BASE_URL or "http://127.0.0.1:11434").rstrip("/")
                if base_url.endswith("/v1"):
                    base_url = base_url[:-3]
                return OllamaLLMProvider(
                    base_url=base_url,
                    model=config.model or settings.OLLAMA_MODEL or "qwen3:14b",
                    fallback_model=settings.OLLAMA_FALLBACK_MODEL or "qwen3:8b",
                    timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS or 180,
                )
            elif provider_name == "gemini":
                if not api_key:
                    return None
                return GeminiLLMProvider(
                    api_key=api_key,
                    model=config.model or settings.GEMINI_MODEL,
                    base_url=config.base_url or settings.GEMINI_BASE_URL,
                    timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
                )
            elif provider_name == "openrouter":
                if not api_key:
                    return None
                return OpenRouterLLMProvider(
                    api_key=api_key,
                    model=config.model or settings.OPENROUTER_MODEL,
                    base_url=config.base_url or settings.OPENROUTER_BASE_URL,
                    writer_model=config.model or settings.OPENROUTER_WRITER_MODEL,
                    planner_model=config.model or settings.OPENROUTER_PLANNER_MODEL,
                    fallback_model=settings.OPENROUTER_FALLBACK_MODEL,
                )
            else:
                if not api_key:
                    return None
                provider = OpenAILLMProvider(
                    api_key=api_key,
                    model=config.model or settings.OPENAI_MODEL,
                    base_url=config.base_url or settings.OPENAI_BASE_URL,
                )
                provider.provider_name = provider_name
                return provider
        except Exception as exc:
            logger.warning("AgentRouter: could not build provider %s: %s", provider_name, exc)
            return None

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
    provider = router.get_provider(agent_id, project_id=project_id)
    start = time.perf_counter()
    error: str | None = None
    status = "success"
    response = ""

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

    call_result = AgentCallResult(
        agent_id=agent_id,
        provider_name=provider.provider_name,
        model_name=provider.model_name,
        duration_ms=duration_ms,
        status=status,
        error=error,
    )

    if db is not None and status == "success":
        try:
            from app.models.ai_usage_log import AiUsageLog
            log_entry = AiUsageLog(
                agent_id=agent_id,
                provider_name=provider.provider_name,
                model_name=provider.model_name,
                project_id=project_id,
                article_id=article_id,
                duration_ms=duration_ms,
                status=status,
                error_message=error,
            )
            db.add(log_entry)
            db.commit()
        except Exception:
            logger.warning("Failed to log AI usage", exc_info=True)

    return response, call_result
