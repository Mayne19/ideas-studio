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


def test_proofreader_role_uses_dedicated_model():
    from app.services.agents.agent_router import _apply_openrouter_role_model

    provider = OpenRouterLLMProvider(api_key="k", model="base", planner_model="plan", proofreader_model="proof")
    assert _apply_openrouter_role_model(provider, "language_quality").model == "proof"
    assert _apply_openrouter_role_model(provider, "fact_checker").model == "plan"


def test_proofreader_role_defaults_to_planner_model():
    provider = OpenRouterLLMProvider(api_key="k", model="base", planner_model="plan")
    assert provider.for_role("proofreader").model == "plan"


def test_cms_binding_model_wins_over_proofreader_env(monkeypatch):
    from types import SimpleNamespace
    from app.core.config import settings
    from app.services.agents.agent_router import _apply_openrouter_role_model
    from app.services.providers.llm_provider import build_provider_from_config

    monkeypatch.setattr(settings, "OPENROUTER_PROOFREADER_MODEL", "env-proof")
    monkeypatch.setattr("app.core.security.decrypt_secret", lambda value: value)
    config = SimpleNamespace(provider="openrouter", api_key_encrypted="k", model="cms-model", base_url=None, reasoning_mode="off")
    provider = build_provider_from_config(config)
    assert _apply_openrouter_role_model(provider, "language_quality").model == "cms-model"
