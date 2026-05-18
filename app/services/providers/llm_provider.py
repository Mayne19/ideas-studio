import json
from abc import ABC, abstractmethod


class ProviderUnavailableError(RuntimeError):
    """Raised when a real LLM provider cannot be reached."""


class GenerationFailedError(RuntimeError):
    """Raised when a real LLM provider returns unusable content."""


class LLMProvider(ABC):
    is_mock: bool = False
    provider_name: str = "unknown"
    model_name: str | None = None

    @abstractmethod
    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        ...

    @abstractmethod
    def generate_json(self, prompt: str, schema_hint: str | None = None):
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    def describe(self) -> str:
        model_part = f" model={self.model_name}" if self.model_name else ""
        return f"{self.provider_name}{model_part} mock={self.is_mock}"


class MockLLMProvider(LLMProvider):
    """Always available; returns template-based text for dev and tests."""
    is_mock: bool = True
    provider_name: str = "mock"
    model_name: str | None = "template"

    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        # Return a short but structured mock response
        return f"[Mock] Contenu généré pour : {prompt[:80].strip()}..."

    def generate_json(self, prompt: str, schema_hint: str | None = None):
        return {}

    def is_available(self) -> bool:
        return True


class OllamaLLMProvider(LLMProvider):
    """Uses a local Ollama instance for generation."""
    is_mock: bool = False
    provider_name: str = "ollama"

    def __init__(self, base_url: str, model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_name = model

    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        try:
            import httpx
            payload: dict = {"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": temperature}}
            if system:
                payload["system"] = system
            resp = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=90)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as exc:
            raise ProviderUnavailableError("Provider IA indisponible, génération réelle impossible.") from exc

    def generate_json(self, prompt: str, schema_hint: str | None = None):
        full_prompt = prompt
        if schema_hint:
            full_prompt += f"\n\nRéponds UNIQUEMENT avec un JSON valide respectant ce schéma : {schema_hint}"
        text = self.generate_text(full_prompt, temperature=0.2)
        try:
            object_start = text.find("{")
            object_end = text.rfind("}")
            array_start = text.find("[")
            array_end = text.rfind("]")
            if object_start >= 0 and object_end > object_start:
                return json.loads(text[object_start:object_end + 1])
            if array_start >= 0 and array_end > array_start:
                return json.loads(text[array_start:array_end + 1])
        except Exception:
            pass
        return {}

    def is_available(self) -> bool:
        try:
            import httpx
            httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return True
        except Exception:
            return False


def get_llm_provider() -> LLMProvider:
    from app.core.config import settings
    from app.services.providers.openai_provider import OpenAILLMProvider
    from app.services.providers.openrouter_provider import OpenRouterLLMProvider

    def _mock_or_raise(reason: str) -> LLMProvider:
        if settings.APP_ENV.lower() in {"production", "staging"}:
            raise ProviderUnavailableError(f"Aucun provider IA disponible. Configure OPENROUTER_API_KEY ou démarre Ollama. {reason}")
        return MockLLMProvider()

    def _try_openrouter() -> LLMProvider | None:
        if not settings.OPENROUTER_API_KEY:
            return None
        provider = OpenRouterLLMProvider(
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.OPENROUTER_MODEL,
            base_url=settings.OPENROUTER_BASE_URL,
            writer_model=settings.OPENROUTER_WRITER_MODEL,
            planner_model=settings.OPENROUTER_PLANNER_MODEL,
            fallback_model=settings.OPENROUTER_FALLBACK_MODEL,
        )
        if provider.is_available():
            return provider
        return None

    def _try_ollama() -> LLMProvider | None:
        if not settings.OLLAMA_URL:
            return None
        provider = OllamaLLMProvider(settings.OLLAMA_URL, settings.OLLAMA_MODEL)
        if provider.is_available():
            return provider
        return None

    def _try_openai() -> LLMProvider | None:
        if not settings.OPENAI_API_KEY:
            return None
        provider = OpenAILLMProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL,
        )
        if provider.is_available():
            return provider
        return None

    requested = settings.DEFAULT_LLM_PROVIDER

    # Auto mode: OpenRouter > Ollama > OpenAI
    if requested == "auto":
        for try_provider in (_try_openrouter, _try_ollama, _try_openai):
            p = try_provider()
            if p is not None:
                return p
        return _mock_or_raise("Aucun provider IA disponible.")

    if requested == "openrouter":
        p = _try_openrouter()
        if p is not None:
            return p
        return _mock_or_raise("OpenRouter configuré mais indisponible.")

    if requested == "openai":
        p = _try_openai()
        if p is not None:
            return p
        return _mock_or_raise("OpenAI configuré mais indisponible.")

    if requested == "ollama":
        p = _try_ollama()
        if p is not None:
            return p
        return _mock_or_raise("Ollama configuré mais indisponible.")

    if requested == "mock":
        return MockLLMProvider()

    return _mock_or_raise(f"Provider '{requested}' non supporté.")
