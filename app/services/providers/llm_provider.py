import json
from abc import ABC, abstractmethod

from sqlalchemy.exc import SQLAlchemyError


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
    """Uses a local Ollama instance for generation — free, no API key needed."""
    is_mock: bool = False
    provider_name: str = "ollama"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3:14b",
        fallback_model: str | None = None,
        timeout_seconds: int = 180,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.model_name = model
        self.fallback_model = fallback_model
        self.timeout_seconds = timeout_seconds
        self._model_checked = False
        self._model_available = False

    def _ensure_model(self):
        if self._model_checked:
            return self._model_available
        self._model_checked = True
        try:
            import httpx
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            available = [m["name"] for m in models]
            if self.model in available:
                self._model_available = True
            elif self.fallback_model and self.fallback_model in available:
                self.model = self.fallback_model
                self.model_name = self.fallback_model
                self._model_available = True
            else:
                self._last_error = f"Modèle Ollama '{self.model}' non disponible. Modèles trouvés: {', '.join(available) if available else 'aucun'}"
                self._model_available = False
        except httpx.ConnectError:
            self._last_error = f"Ollama local indisponible sur {self.base_url}"
            self._model_available = False
        except Exception as exc:
            self._last_error = f"Erreur Ollama: {exc}"
            self._model_available = False
        return self._model_available

    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        import httpx
        if not self._ensure_model():
            raise ProviderUnavailableError(self._last_error or "Aucun modèle Ollama disponible")
        try:
            messages: list[dict[str, str]] = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            }
            resp = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout_seconds)
            if resp.status_code == 404:
                raise ProviderUnavailableError(
                    f"Modèle Ollama '{self.model}' non trouvé. Lancez: ollama pull {self.model}"
                )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            if not content:
                raise ProviderUnavailableError("Ollama a retourné une réponse vide")
            return content.strip()
        except ProviderUnavailableError:
            raise
        except httpx.ConnectError:
            raise ProviderUnavailableError(f"Ollama local indisponible sur {self.base_url}")
        except httpx.TimeoutException:
            raise ProviderUnavailableError(
                f"Ollama modèle {self.model} : timeout après {self.timeout_seconds}s"
            )
        except Exception as exc:
            raise ProviderUnavailableError(f"Ollama: {exc}") from exc

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
        return self._ensure_model()

    def health_check(self) -> dict:
        """Return structured health status (does NOT raise)."""
        try:
            import httpx
            tags_resp = httpx.get(f"{self.base_url}/api/tags", timeout=10)
            if tags_resp.status_code != 200:
                return {"provider": "ollama", "model": self.model, "configured": True, "available": False, "error": f"Ollama API erreur HTTP {tags_resp.status_code}"}
            models = tags_resp.json().get("models", [])
            available = [m["name"] for m in models]
            if self.model in available:
                return {"provider": "ollama", "model": self.model, "configured": True, "available": True}
            if self.fallback_model and self.fallback_model in available:
                return {"provider": "ollama", "model": self.fallback_model, "configured": True, "available": True}
            return {
                "provider": "ollama", "model": self.model, "configured": True, "available": False,
                "error": f"Modèle '{self.model}' non disponible. Modèles trouvés: {', '.join(available) if available else 'aucun'}. Lancez: ollama pull {self.model}",
            }
        except httpx.ConnectError:
            return {"provider": "ollama", "model": self.model, "configured": True, "available": False, "error": f"Ollama local indisponible sur {self.base_url}"}
        except Exception as exc:
            return {"provider": "ollama", "model": self.model, "configured": True, "available": False, "error": str(exc)}


def get_llm_provider() -> LLMProvider:
    from app.core.config import settings
    from app.services.providers.openai_provider import OpenAILLMProvider
    from app.services.providers.openrouter_provider import OpenRouterLLMProvider
    from app.services.providers.gemini_provider import GeminiLLMProvider

    def _raise_or_raise(reason: str) -> LLMProvider:
        raise ProviderUnavailableError(f"Aucun provider IA réel disponible. Configure OPENROUTER_API_KEY ou démarre Ollama. {reason}")

    def _from_db_default() -> LLMProvider | None:
        if settings.APP_ENV == "test":
            return None
        try:
            from app.core.database import SessionLocal
            from app.core.security import decrypt_secret
            from app.models.ai_provider_config import AIProviderConfig
        except Exception:
            return None

        db = SessionLocal()
        try:
            config = db.query(AIProviderConfig).filter(
                AIProviderConfig.is_default == True,
                AIProviderConfig.enabled == True,
            ).first()
            if not config:
                return None
            api_key = decrypt_secret(config.api_key_encrypted)
            provider_name = config.provider

            if provider_name == "ollama":
                base_url = (config.base_url or settings.OLLAMA_BASE_URL or settings.OLLAMA_URL or "http://127.0.0.1:11434").rstrip("/")
                if base_url.endswith("/v1"):
                    base_url = base_url[:-3]
                provider = OllamaLLMProvider(
                    base_url=base_url,
                    model=config.model or settings.OLLAMA_MODEL or "qwen3:14b",
                    fallback_model=settings.OLLAMA_FALLBACK_MODEL or "qwen3:8b",
                    timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS or 180,
                )
            elif provider_name == "gemini":
                if not api_key:
                    return None
                provider = GeminiLLMProvider(
                    api_key=api_key,
                    model=config.model or settings.GEMINI_MODEL,
                    base_url=config.base_url or settings.GEMINI_BASE_URL,
                    timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
                )
            elif provider_name == "openrouter":
                if not api_key:
                    return None
                provider = OpenRouterLLMProvider(
                    api_key=api_key,
                    model=config.model or settings.OPENROUTER_MODEL,
                    base_url=config.base_url or settings.OPENROUTER_BASE_URL,
                    writer_model=config.model or settings.OPENROUTER_WRITER_MODEL,
                    planner_model=config.model or settings.OPENROUTER_PLANNER_MODEL,
                    fallback_model=settings.OPENROUTER_FALLBACK_MODEL,
                )
            elif provider_name in {"openai", "custom"}:
                if not api_key:
                    return None
                provider = OpenAILLMProvider(
                    api_key=api_key,
                    model=config.model or settings.OPENAI_MODEL,
                    base_url=config.base_url or settings.OPENAI_BASE_URL,
                )
                provider.provider_name = provider_name
            else:
                return None

            if provider.is_available():
                return provider
            return None
        except SQLAlchemyError:
            return None
        finally:
            db.close()

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
        base_url = settings.OLLAMA_BASE_URL or settings.OLLAMA_URL or "http://127.0.0.1:11434"
        if not base_url:
            return None
        provider = OllamaLLMProvider(
            base_url=base_url,
            model=settings.OLLAMA_MODEL or "qwen3:14b",
            fallback_model=settings.OLLAMA_FALLBACK_MODEL or "qwen3:8b",
            timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS or 180,
        )
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

    if requested == "mock":
        return MockLLMProvider()

    db_provider = _from_db_default()
    if db_provider is not None:
        return db_provider

    # Auto mode: OpenRouter > Ollama > OpenAI
    if requested == "auto":
        for try_provider in (_try_openrouter, _try_ollama, _try_openai):
            p = try_provider()
            if p is not None:
                return p
        return _raise_or_raise("Aucun provider IA disponible.")

    if requested == "openrouter":
        p = _try_openrouter()
        if p is not None:
            return p
        return _raise_or_raise("OpenRouter configuré mais indisponible.")

    if requested == "openai":
        p = _try_openai()
        if p is not None:
            return p
        return _raise_or_raise("OpenAI configuré mais indisponible.")

    if requested == "ollama":
        p = _try_ollama()
        if p is not None:
            return p
        return _raise_or_raise("Ollama configuré mais indisponible.")

    if requested == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ProviderUnavailableError(
                "GEMINI_API_KEY non configurée. Ajoute GEMINI_API_KEY dans le .env ou les variables Render."
            )
        provider = GeminiLLMProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
            base_url=settings.GEMINI_BASE_URL,
            timeout_seconds=settings.GEMINI_TIMEOUT_SECONDS,
        )
        if provider.is_available():
            return provider
        return _raise_or_raise("Gemini configuré mais indisponible (clé invalide ou API saturée).")

    return _raise_or_raise(f"Provider '{requested}' non supporté.")
