import json
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    is_mock: bool = False

    @abstractmethod
    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        ...

    @abstractmethod
    def generate_json(self, prompt: str, schema_hint: str | None = None) -> dict:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


class MockLLMProvider(LLMProvider):
    """Always available; returns template-based text for dev and tests."""
    is_mock: bool = True

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

    def __init__(self, base_url: str, model: str = "llama3.2"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        try:
            import httpx
            payload: dict = {"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": temperature}}
            if system:
                payload["system"] = system
            resp = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=90)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception:
            return ""

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
    if settings.DEFAULT_LLM_PROVIDER == "ollama" and settings.OLLAMA_URL:
        provider = OllamaLLMProvider(settings.OLLAMA_URL, settings.OLLAMA_MODEL)
        if provider.is_available():
            return provider
    return MockLLMProvider()
