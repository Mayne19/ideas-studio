"""Génération d'images d'illustration via OpenRouter (chat completions avec
sortie image).

Aucune nouvelle clé : on réutilise la clé OpenRouter déjà configurée dans
Paramètres → Providers IA (ai.provider_credentials, chiffrée), projet puis
globale, puis OPENROUTER_API_KEY en dernier repli (infra).

OpenRouter renvoie les images générées dans
choices[0].message.images[].image_url.url sous forme de data URL base64
(« data:image/png;base64,... »).
"""
from __future__ import annotations

import base64
import binascii
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_IMAGE_MODEL = "google/gemini-3.1-flash-lite-image"

# Modèles OpenRouter dont output_modalities contient "image". Coût indicatif
# par image (USD) affiché dans les paramètres et utilisé comme estimation
# quand OpenRouter ne renvoie pas le coût réel (usage.cost).
IMAGE_MODELS: dict[str, dict] = {
    "google/gemini-3.1-flash-lite-image": {"label": "Gemini 3.1 Flash Lite Image (économique)", "approx_cost_usd": 0.002},
    "google/gemini-3.1-flash-image": {"label": "Gemini 3.1 Flash Image", "approx_cost_usd": 0.04},
    "google/gemini-2.5-flash-image": {"label": "Gemini 2.5 Flash Image", "approx_cost_usd": 0.04},
}

_DATA_URL_RE = re.compile(r"^data:(?P<mime>image/[\w.+-]+)?(?P<params>(;[\w-]+=[^;,]*)*)(?P<b64>;base64)?,(?P<data>.*)$", re.DOTALL)


class ImageGenerationError(RuntimeError):
    """Échec de génération (clé absente, refus du modèle, réponse sans image)."""


@dataclass
class GeneratedImage:
    data: bytes
    mime_type: str
    model: str
    # Coût réel renvoyé par OpenRouter (usage.cost, en USD) si disponible.
    cost_usd: float | None = None
    usage: dict = field(default_factory=dict)


def approx_cost_usd(model: str | None) -> float | None:
    return (IMAGE_MODELS.get(model or "") or {}).get("approx_cost_usd")


def parse_data_url(url: str) -> tuple[bytes, str]:
    """Décode une data URL base64 en (octets, type MIME). Lève
    ImageGenerationError si la valeur n'est pas une image base64 valide."""
    if not isinstance(url, str):
        raise ImageGenerationError("URL d'image absente")
    match = _DATA_URL_RE.match(url.strip())
    if not match or not match.group("b64"):
        raise ImageGenerationError("Format d'image inattendu (data URL base64 attendue)")
    try:
        data = base64.b64decode(match.group("data"), validate=False)
    except (binascii.Error, ValueError) as exc:
        raise ImageGenerationError(f"Image base64 illisible : {exc}") from exc
    if not data:
        raise ImageGenerationError("Image vide")
    return data, match.group("mime") or "image/png"


def extract_image_from_response(payload: dict) -> str:
    """Première image (data URL) de la réponse chat completions OpenRouter."""
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not choices:
        error = (payload or {}).get("error") if isinstance(payload, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        raise ImageGenerationError(message or "Réponse sans choix")
    message = (choices[0] or {}).get("message") or {}
    for image in message.get("images") or []:
        url = ((image or {}).get("image_url") or {}).get("url")
        if url:
            return url
    # Certains modèles renvoient un refus en texte plutôt qu'une image.
    text = message.get("content")
    hint = f" (réponse texte : {str(text)[:160]})" if text else ""
    raise ImageGenerationError(f"Le modèle n'a renvoyé aucune image{hint}")


class OpenRouterImageProvider:
    provider_name = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_IMAGE_MODEL,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: int = 120,
        http_post=None,
    ):
        self.api_key = api_key
        self.model = model or DEFAULT_IMAGE_MODEL
        self.base_url = (base_url or "https://openrouter.ai/api/v1").rstrip("/")
        self.timeout_seconds = timeout_seconds
        # Injection pour les tests hors ligne.
        self._http_post = http_post

    def build_payload(self, prompt: str, aspect_ratio: str = "16:9") -> dict:
        return {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "image_config": {"aspect_ratio": aspect_ratio},
            # Coût réel (USD) dans usage.cost : suivi des dépenses.
            "usage": {"include": True},
        }

    def generate(self, prompt: str, aspect_ratio: str = "16:9") -> GeneratedImage:
        import httpx

        from app.services.providers.llm_provider import run_with_deadline

        post = self._http_post or httpx.post
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Ideas Studio",
        }
        try:
            resp = run_with_deadline(
                post,
                (f"{self.base_url}/chat/completions",),
                {"json": self.build_payload(prompt, aspect_ratio), "headers": headers, "timeout": self.timeout_seconds},
                seconds=self.timeout_seconds + 30,
                message=f"Génération d'image {self.model} : délai dépassé",
            )
            resp.raise_for_status()
            payload = resp.json()
        except ImageGenerationError:
            raise
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (401, 403):
                raise ImageGenerationError("Clé OpenRouter refusée") from exc
            if status == 402:
                raise ImageGenerationError("Crédits OpenRouter insuffisants") from exc
            if status == 429:
                raise ImageGenerationError("Quota OpenRouter dépassé (HTTP 429)") from exc
            raise ImageGenerationError(f"Appel OpenRouter échoué : {exc}") from exc

        data, mime = parse_data_url(extract_image_from_response(payload))
        usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
        cost = usage.get("cost")
        try:
            cost = float(cost) if cost is not None else None
        except (TypeError, ValueError):
            cost = None
        return GeneratedImage(data=data, mime_type=mime, model=self.model, cost_usd=cost, usage=usage)


def resolve_openrouter_key(db, project_id: str | None) -> tuple[str, str | None] | None:
    """(clé, base_url) OpenRouter : credential projet, puis globale
    (Paramètres → Providers IA), puis OPENROUTER_API_KEY. None si aucune."""
    from app.core.config import settings

    if db is not None:
        try:
            from sqlalchemy import select

            from app.core.security import decrypt_secret
            from app.models.ai import Provider
            from app.services.providers.provider_config import _credential_for

            provider_row = db.execute(select(Provider).where(Provider.code == "openrouter")).scalar_one_or_none()
            if provider_row is not None and provider_row.is_enabled:
                cred = _credential_for(db, provider_row.id, project_id)
                api_key = decrypt_secret(cred.secret_ref) if cred is not None else None
                if api_key:
                    return api_key, provider_row.base_url
        except Exception as exc:
            logger.warning("image generation: lecture de la clé OpenRouter impossible (%s)", exc)
    if settings.OPENROUTER_API_KEY:
        return settings.OPENROUTER_API_KEY, settings.OPENROUTER_BASE_URL
    return None


def get_image_provider(db, project_id: str | None, model: str | None = None) -> OpenRouterImageProvider | None:
    resolved = resolve_openrouter_key(db, project_id)
    if resolved is None:
        return None
    api_key, base_url = resolved
    return OpenRouterImageProvider(api_key=api_key, model=model or DEFAULT_IMAGE_MODEL, base_url=base_url or "https://openrouter.ai/api/v1")
