from app.services.providers.openai_provider import OpenAILLMProvider


class GeminiLLMProvider(OpenAILLMProvider):
    """Gemini via OpenAI-compatible endpoint — simple, stable, no auto-fallback."""
    provider_name: str = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout_seconds: int = 180,
    ):
        if not api_key:
            raise ValueError("GEMINI_API_KEY non configurée. Ajoute GEMINI_API_KEY dans le .env")
        super().__init__(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=1,
        )
