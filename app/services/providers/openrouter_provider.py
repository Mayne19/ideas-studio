from app.services.providers.openai_provider import OpenAILLMProvider


class OpenRouterLLMProvider(OpenAILLMProvider):
    provider_name: str = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-2.0-flash-001",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 120,
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
