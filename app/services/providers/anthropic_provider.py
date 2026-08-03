"""Provider Anthropic (Claude) basé sur le SDK officiel — Messages API."""
import json
import logging

from app.services.providers.llm_provider import LLMProvider, ProviderUnavailableError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"


class AnthropicLLMProvider(LLMProvider):
    is_mock: bool = False
    provider_name: str = "anthropic"

    def __init__(
        self,
        api_key: str,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 180,
        max_tokens: int = 16000,
    ):
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self.model_name = self.model
        self.base_url = base_url or None
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self._client = None
        self.last_usage: dict[str, int] | None = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            kwargs = {"api_key": self.api_key, "timeout": float(self.timeout_seconds)}
            # Les configs stockent parfois l'URL de base OpenAI-compatible ("/v1") : le SDK attend l'hôte nu.
            if self.base_url:
                kwargs["base_url"] = self.base_url.rstrip("/").removesuffix("/v1")
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        # temperature est ignoré : les modèles Claude récents (Opus 5+) rejettent ce paramètre.
        import anthropic

        self.last_usage = None
        try:
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            response = self._get_client().messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise ProviderUnavailableError(f"Anthropic : clé API invalide ({exc.message})") from exc
        except anthropic.NotFoundError as exc:
            raise ProviderUnavailableError(
                f"Anthropic : modèle '{self.model}' introuvable ({exc.message})"
            ) from exc
        except anthropic.RateLimitError as exc:
            raise ProviderUnavailableError("Anthropic : limite de débit atteinte, réessayez plus tard") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderUnavailableError(f"Anthropic : erreur API {exc.status_code} ({exc.message})") from exc
        except anthropic.APIConnectionError as exc:
            raise ProviderUnavailableError(f"Anthropic : connexion impossible ({exc})") from exc

        usage = getattr(response, "usage", None)
        if usage is not None:
            self.last_usage = {
                "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            }

        if response.stop_reason == "refusal":
            raise ProviderUnavailableError(
                "Anthropic : la requête a été refusée par les garde-fous du modèle."
            )
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise ProviderUnavailableError("Anthropic a retourné une réponse vide")
        return text

    def generate_json(self, prompt: str, schema_hint: str | None = None):
        full_prompt = prompt
        if schema_hint:
            full_prompt += f"\n\nRéponds UNIQUEMENT avec un JSON valide respectant ce schéma : {schema_hint}"
        text = self.generate_text(full_prompt)
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
        if not self.api_key:
            return False
        try:
            self._get_client().models.retrieve(self.model)
            return True
        except Exception as exc:
            logger.warning("Anthropic indisponible (model=%s): %s", self.model, exc)
            return False
