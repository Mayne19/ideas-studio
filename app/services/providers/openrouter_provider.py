from app.services.providers.openai_provider import OpenAILLMProvider


class OpenRouterLLMProvider(OpenAILLMProvider):
    provider_name: str = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek/deepseek-v4-flash:free",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 180,
        max_retries: int = 3,
        writer_model: str | None = None,
        planner_model: str | None = None,
        fallback_model: str | None = None,
    ):
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self.writer_model = writer_model or model
        self.planner_model = planner_model or model
        self.fallback_model = fallback_model or model
