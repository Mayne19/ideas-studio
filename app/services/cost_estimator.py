from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

MODEL_PRICES_EUR: dict[str, dict[str, float]] = {
    # Gemini
    "gemini/gemini-2.5-flash": {"input_per_1k": 0.000075, "output_per_1k": 0.00030},
    "gemini/gemini-2.5-pro": {"input_per_1k": 0.00125, "output_per_1k": 0.00500},
    "gemini/gemini-2.0-flash": {"input_per_1k": 0.000075, "output_per_1k": 0.00030},
    # OpenAI
    "openai/gpt-4o-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.00060},
    "openai/gpt-4o": {"input_per_1k": 0.00250, "output_per_1k": 0.01000},
    "openai/gpt-4.1-mini": {"input_per_1k": 0.00015, "output_per_1k": 0.00060},
    "openai/gpt-4.1-nano": {"input_per_1k": 0.00010, "output_per_1k": 0.00040},
    # Claude
    "anthropic/claude-sonnet": {"input_per_1k": 0.00300, "output_per_1k": 0.01500},
    "anthropic/claude-haiku": {"input_per_1k": 0.00025, "output_per_1k": 0.00125},
    # Mistral
    "mistral/mistral-small-latest": {"input_per_1k": 0.00100, "output_per_1k": 0.00200},
    "mistral/mistral-medium-latest": {"input_per_1k": 0.00275, "output_per_1k": 0.00810},
    # DeepSeek via OpenRouter
    "deepseek/deepseek-v4-flash:free": {"input_per_1k": 0.0, "output_per_1k": 0.0},
    "deepseek/deepseek-chat": {"input_per_1k": 0.00015, "output_per_1k": 0.00060},
    # Free / Ollama
    "ollama/qwen3:14b": {"input_per_1k": 0.0, "output_per_1k": 0.0},
    "ollama/qwen3:8b": {"input_per_1k": 0.0, "output_per_1k": 0.0},
}

FALLBACK_PRICE = {"input_per_1k": 0.0, "output_per_1k": 0.0}


def get_model_price(provider: str, model: str | None) -> dict[str, float] | None:
    key = f"{provider}/{model}" if model else provider
    price = MODEL_PRICES_EUR.get(key)
    if price is not None:
        return price
    # Try without free suffix
    if model and ":free" in model:
        key2 = f"{provider}/{model.replace(':free', '')}"
        price = MODEL_PRICES_EUR.get(key2)
        if price is not None:
            return price
    # Try generic provider-level price
    generic = MODEL_PRICES_EUR.get(provider)
    return generic


def estimate_call_cost(
    provider: str,
    model: str | None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    prompt_chars: int | None = None,
    response_chars: int | None = None,
) -> dict[str, Any]:
    price = get_model_price(provider, model)
    model_key = f"{provider}/{model}" if model else provider

    if input_tokens is None and prompt_chars is not None:
        input_tokens = max(1, prompt_chars // 4)
    if output_tokens is None and response_chars is not None:
        output_tokens = max(1, response_chars // 4)
    if input_tokens is None:
        input_tokens = 500
    if output_tokens is None:
        output_tokens = 500

    if price is not None:
        input_cost = (input_tokens / 1000.0) * price["input_per_1k"]
        output_cost = (output_tokens / 1000.0) * price["output_per_1k"]
        total = round(input_cost + output_cost, 6)
        return {
            "estimated_cost_eur": total,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "price_source": "configured_price_table",
            "cost_status": "estimated",
            "model_key": model_key,
        }
    else:
        return {
            "estimated_cost_eur": None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "price_source": "unknown",
            "cost_status": "unknown_price",
            "model_key": model_key,
        }


def estimate_workflow_cost(
    agent_calls: list[dict[str, Any]],
    cost_limit_eur: float | None = None,
) -> dict[str, Any]:
    breakdown = []
    total_estimated = 0.0
    has_unknown = False
    warnings: list[str] = []

    for call in agent_calls:
        agent_key = call.get("agent_key", "unknown")
        provider = call.get("provider", "unknown")
        model = call.get("model")
        input_tokens = call.get("estimated_input_tokens")
        output_tokens = call.get("estimated_output_tokens")

        est = estimate_call_cost(provider, model, input_tokens, output_tokens)
        cost = est["estimated_cost_eur"]
        if cost is None:
            has_unknown = True
            warnings.append(f"Prix inconnu pour {provider}/{model or '?'} (agent: {agent_key})")
        else:
            total_estimated += cost

        breakdown.append({
            "agent_key": agent_key,
            "provider": provider,
            "model": model or "",
            "estimated_input_tokens": est["input_tokens"],
            "estimated_output_tokens": est["output_tokens"],
            "estimated_cost_eur": cost if cost is not None else 0,
            "price_source": est["price_source"],
        })

    total_estimated = round(total_estimated, 6)

    if cost_limit_eur is not None and total_estimated > cost_limit_eur:
        cost_status = "over_limit"
        warnings.append(f"Coût estimé ({total_estimated} EUR) dépasse la limite ({cost_limit_eur} EUR)")
    elif has_unknown:
        cost_status = "partial_unknown"
    else:
        cost_status = "within_limit"

    return {
        "estimated_cost_eur": total_estimated,
        "currency": "EUR",
        "cost_limit_eur": cost_limit_eur,
        "cost_status": cost_status,
        "estimation_quality": "estimated" if not has_unknown else "partial",
        "breakdown": breakdown,
        "warnings": warnings,
    }
