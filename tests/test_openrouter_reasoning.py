from app.services.providers.openrouter_provider import OpenRouterLLMProvider


def test_reasoning_disabled_by_default():
    provider = OpenRouterLLMProvider(api_key="k", model="deepseek/deepseek-v4-flash")
    assert provider._extra_payload() == {"reasoning": {"enabled": False}}


def test_reasoning_auto_leaves_model_default():
    provider = OpenRouterLLMProvider(api_key="k", model="m", reasoning_mode="auto")
    assert provider._extra_payload() == {}
    assert provider.for_role("writer")._extra_payload() == {}


def test_mandatory_reasoning_model_retries_without_param(monkeypatch):
    import httpx

    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append(dict(json))
        request = httpx.Request("POST", url)
        if "reasoning" in json:
            return httpx.Response(400, json={"error": {"message": "Reasoning is mandatory for this endpoint and cannot be disabled."}}, request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}], "usage": {}}, request=request)

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = OpenRouterLLMProvider(api_key="k", model="google/gemini-3.8-flash", max_retries=1)
    assert provider.generate_text("x") == "ok"
    assert "reasoning" in calls[0] and "reasoning" not in calls[1]
