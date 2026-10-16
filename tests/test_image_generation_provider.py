"""Provider de génération d'images OpenRouter : tests hors ligne (faux HTTP)."""
import base64

import pytest

from app.services.providers.image_generation_provider import (
    DEFAULT_IMAGE_MODEL,
    ImageGenerationError,
    OpenRouterImageProvider,
    extract_image_from_response,
    parse_data_url,
)

PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-image-bytes"
DATA_URL = "data:image/png;base64," + base64.b64encode(PNG_BYTES).decode()


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            raise httpx.HTTPStatusError("err", request=request, response=httpx.Response(self.status_code, request=request))

    def json(self):
        return self._payload


def _openrouter_payload(url=DATA_URL, cost=0.0021):
    return {
        "choices": [{"message": {"role": "assistant", "content": "", "images": [
            {"type": "image_url", "image_url": {"url": url}},
        ]}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 1290, "cost": cost},
    }


def test_parse_data_url_decodes_base64():
    data, mime = parse_data_url(DATA_URL)
    assert data == PNG_BYTES
    assert mime == "image/png"


def test_parse_data_url_rejects_non_base64_or_http_urls():
    with pytest.raises(ImageGenerationError):
        parse_data_url("https://example.com/image.png")
    with pytest.raises(ImageGenerationError):
        parse_data_url("data:image/png,rawdata")


def test_extract_image_reports_text_refusal():
    payload = {"choices": [{"message": {"content": "I cannot draw that."}}]}
    with pytest.raises(ImageGenerationError, match="aucune image"):
        extract_image_from_response(payload)


def test_generate_sends_image_modalities_and_parses_cost():
    calls = []

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers})
        return _Resp(_openrouter_payload())

    provider = OpenRouterImageProvider(api_key="sk-or-test", http_post=fake_post)
    image = provider.generate("a calm illustration")

    assert image.data == PNG_BYTES
    assert image.mime_type == "image/png"
    assert image.model == DEFAULT_IMAGE_MODEL
    assert image.cost_usd == pytest.approx(0.0021)
    sent = calls[0]
    assert sent["url"].endswith("/chat/completions")
    assert sent["json"]["modalities"] == ["image", "text"]
    assert sent["json"]["model"] == DEFAULT_IMAGE_MODEL
    assert sent["headers"]["Authorization"] == "Bearer sk-or-test"


def test_generate_maps_http_errors_to_image_generation_error():
    provider = OpenRouterImageProvider(api_key="k", http_post=lambda *a, **kw: _Resp({}, status=402))
    with pytest.raises(ImageGenerationError, match="Crédits"):
        provider.generate("x")
