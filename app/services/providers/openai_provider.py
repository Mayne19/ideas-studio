import json

import httpx

from app.services.providers.llm_provider import LLMProvider, ProviderUnavailableError


class OpenAILLMProvider(LLMProvider):
    is_mock: bool = False
    provider_name: str = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: int = 90,
    ):
        self.api_key = api_key
        self.model = model
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def generate_text(self, prompt: str, system: str | None = None, temperature: float = 0.7) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise ProviderUnavailableError("Provider IA indisponible, génération réelle impossible.") from exc

    def generate_json(self, prompt: str, schema_hint: str | None = None):
        full_prompt = prompt
        if schema_hint:
            full_prompt += f"\n\nRéponds UNIQUEMENT avec un JSON valide respectant ce schéma : {schema_hint}"
        raw = self.generate_text(full_prompt, temperature=0.2)
        try:
            start_obj = raw.find("{")
            end_obj = raw.rfind("}")
            if start_obj >= 0 and end_obj > start_obj:
                return json.loads(raw[start_obj:end_obj + 1])
        except Exception:
            pass
        return {}

    def is_available(self) -> bool:
        if not self.api_key or not self.model:
            return False
        try:
            resp = httpx.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=10,
            )
            return resp.status_code < 400
        except Exception:
            return False
