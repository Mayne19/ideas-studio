import json
import time

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
        max_retries: int = 2,
    ):
        self.api_key = api_key
        self.model = model
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

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

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = httpx.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                    timeout=self.timeout_seconds,
                )
                if resp.status_code == 429 and attempt < self.max_retries:
                    delay = 3 * (2 ** attempt)
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content is None:
                    raise ProviderUnavailableError(
                        f"Provider {self.provider_name} model {self.model} a retourné content=null "
                        "(mode raisonnement activé sans réponse textuelle)."
                    )
                return content.strip()
            except ProviderUnavailableError:
                raise
            except httpx.HTTPStatusError as exc:
                detail = ""
                try:
                    detail = exc.response.json().get("error", {}).get("message", exc.response.text)
                except Exception:
                    detail = exc.response.text[:200]
                last_error = ProviderUnavailableError(
                    f"Provider {self.provider_name} (HTTP {exc.response.status_code}): {detail}"
                )
                if attempt < self.max_retries:
                    time.sleep(3 * (2 ** attempt))
            except httpx.TimeoutException:
                last_error = ProviderUnavailableError(
                    f"Provider {self.provider_name} model {self.model} : timeout après {self.timeout_seconds}s"
                )
                if attempt < self.max_retries:
                    time.sleep(3 * (2 ** attempt))
            except Exception as exc:
                last_error = ProviderUnavailableError(
                    f"Provider IA indisponible ({self.provider_name}): {exc}"
                )
                break

        raise last_error or ProviderUnavailableError(
            f"Provider {self.provider_name} indisponible après {self.max_retries + 1} tentative(s)."
        )

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
