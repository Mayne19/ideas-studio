from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/llm")
def health_llm():
    """Return LLM provider status — available, configured, model, etc."""
    from app.services.providers.llm_provider import (
        OllamaLLMProvider, MockLLMProvider, ProviderUnavailableError,
    )
    from app.services.providers.openai_provider import OpenAILLMProvider
    from app.services.providers.openrouter_provider import OpenRouterLLMProvider

    requested = settings.DEFAULT_LLM_PROVIDER
    mock_allowed = "yes" if requested == "mock" else "no"

    if requested == "mock":
        return {
            "provider": "mock",
            "model": "template",
            "configured": True,
            "available": True,
            "mock_allowed": "yes",
            "environment": settings.APP_ENV,
        }

    if requested == "ollama":
        base_url = settings.OLLAMA_BASE_URL or settings.OLLAMA_URL or "http://127.0.0.1:11434"
        provider = OllamaLLMProvider(
            base_url=base_url,
            model=settings.OLLAMA_MODEL or "qwen3:14b",
            fallback_model=settings.OLLAMA_FALLBACK_MODEL or "qwen3:8b",
            timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS or 180,
        )
        status = provider.health_check()
        status["mock_allowed"] = mock_allowed
        status["environment"] = settings.APP_ENV
        return status

    if requested == "openai":
        if not settings.OPENAI_API_KEY:
            return {
                "provider": "openai",
                "model": settings.OPENAI_MODEL,
                "configured": True,
                "available": False,
                "error": "OPENAI_API_KEY non configurée",
                "mock_allowed": mock_allowed,
                "environment": settings.APP_ENV,
            }
        provider = OpenAILLMProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL or "https://api.openai.com/v1",
        )
        available = provider.is_available()
        return {
            "provider": "openai",
            "model": settings.OPENAI_MODEL,
            "configured": True,
            "available": available,
            "mock_allowed": mock_allowed,
            "environment": settings.APP_ENV,
        }

    if requested == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            return {
                "provider": "openrouter",
                "model": settings.OPENROUTER_MODEL,
                "configured": True,
                "available": False,
                "error": "OPENROUTER_API_KEY non configurée",
                "mock_allowed": mock_allowed,
                "environment": settings.APP_ENV,
            }
        try:
            provider = OpenRouterLLMProvider(
                api_key=settings.OPENROUTER_API_KEY,
                model=settings.OPENROUTER_MODEL,
                base_url=settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1",
            )
            available = provider.is_available()
            return {
                "provider": "openrouter",
                "model": settings.OPENROUTER_MODEL,
                "configured": True,
                "available": available,
                "mock_allowed": mock_allowed,
                "environment": settings.APP_ENV,
            }
        except Exception as exc:
            return {
                "provider": "openrouter",
                "model": settings.OPENROUTER_MODEL,
                "configured": True,
                "available": False,
                "error": str(exc),
                "mock_allowed": mock_allowed,
                "environment": settings.APP_ENV,
            }

    return {
        "provider": requested,
        "model": "",
        "configured": False,
        "available": False,
        "error": f"Provider '{requested}' non supporté",
        "mock_allowed": mock_allowed,
        "environment": settings.APP_ENV,
    }
