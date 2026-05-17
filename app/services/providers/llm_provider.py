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
    def generate_json(self, prompt: str, schema_hint: str | None = None) -> dict:
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

    def generate_json(self, prompt: str, schema_hint: str | None = None) -> dict:
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

    def generate_json(self, prompt: str, schema_hint: str | None = None) -> dict:
        full_prompt = prompt
        if schema_hint:
            full_prompt += f"\n\nRéponds UNIQUEMENT avec un JSON valide respectant ce schéma : {schema_hint}"
        text = self.generate_text(full_prompt, temperature=0.2)
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
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

    def _mock_or_raise(reason: str) -> LLMProvider:
        if settings.APP_ENV.lower() in {"production", "staging"}:
            raise ProviderUnavailableError(f"Provider IA indisponible, génération réelle impossible. {reason}")
        return MockLLMProvider()

    if settings.DEFAULT_LLM_PROVIDER == "ollama" and settings.OLLAMA_URL:
        provider = OllamaLLMProvider(settings.OLLAMA_URL, settings.OLLAMA_MODEL)
        if provider.is_available():
            return provider
        return _mock_or_raise("Ollama est configuré mais inaccessible.")
    if settings.DEFAULT_LLM_PROVIDER == "mock":
        return MockLLMProvider()
    if settings.DEFAULT_LLM_PROVIDER == "ollama":
        return _mock_or_raise("OLLAMA_URL est manquant.")
    return _mock_or_raise(f"Provider '{settings.DEFAULT_LLM_PROVIDER}' non supporté.")
