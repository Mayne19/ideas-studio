from app.services.providers.openrouter_provider import OpenRouterLLMProvider


def test_reasoning_disabled_by_default():
    provider = OpenRouterLLMProvider(api_key="k", model="deepseek/deepseek-v4-flash")
    assert provider._extra_payload() == {"reasoning": {"enabled": False}}


def test_reasoning_auto_leaves_model_default():
    provider = OpenRouterLLMProvider(api_key="k", model="m", reasoning_mode="auto")
    assert provider._extra_payload() == {}
    assert provider.for_role("writer")._extra_payload() == {}
