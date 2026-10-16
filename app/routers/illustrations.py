"""Paramètres → Services externes → Images d'illustration : mode (IA,
Unsplash, aucune), style visuel de marque, et aperçu d'une image générée.
Même modèle d'accès que /settings/external-services (owner/admin du projet,
ou staff pour la configuration globale)."""
import base64
import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.core import User
from app.routers.external_services import _ensure_access
from app.schemas.illustration import (
    IllustrationOption,
    IllustrationPreviewRequest,
    IllustrationPreviewResult,
    IllustrationSettingsPublic,
    IllustrationSettingsUpsert,
)
from app.services.illustration_settings_service import (
    MAX_IMAGES_LIMIT,
    MODES,
    STYLE_PRESETS,
    IllustrationConfig,
    IllustrationSettingsError,
    compose_image_prompt,
    find_row,
    normalize_config,
    resolve_config,
    upsert_config,
)
from app.services.providers.image_generation_provider import (
    IMAGE_MODELS,
    ImageGenerationError,
    approx_cost_usd,
    get_image_provider,
    resolve_openrouter_key,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/illustrations", tags=["external_services"])

PREVIEW_SUBJECT = (
    "An editor reviewing a long article draft at a desk, surrounded by abstract shapes "
    "representing ideas, research notes and connections"
)


def _to_public(db: Session, project_id: str | None) -> IllustrationSettingsPublic:
    effective = resolve_config(db, project_id)
    row = find_row(db, project_id)
    config = {k: v for k, v in effective.to_dict().items() if k not in ("mode", "source")}
    return IllustrationSettingsPublic(
        project_id=project_id,
        configured=row is not None,
        effective_source=effective.source,
        mode=effective.mode,
        config=config,
        modes=[IllustrationOption(code=c, label=label) for c, label in MODES.items()],
        models=[
            IllustrationOption(code=c, label=m["label"], approx_cost_usd=m.get("approx_cost_usd"))
            for c, m in IMAGE_MODELS.items()
        ],
        style_presets=[IllustrationOption(code=c, label=p["label"]) for c, p in STYLE_PRESETS.items()],
        max_images_limit=MAX_IMAGES_LIMIT,
        openrouter_configured=resolve_openrouter_key(db, project_id) is not None,
    )


@router.get("", response_model=IllustrationSettingsPublic)
def get_illustration_settings(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_access(project_id, current_user, db)
    return _to_public(db, project_id)


@router.put("", response_model=IllustrationSettingsPublic)
def save_illustration_settings(
    data: IllustrationSettingsUpsert,
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_access(project_id, current_user, db)
    try:
        upsert_config(db, project_id, data.mode, data.config.model_dump(exclude_none=True))
    except IllustrationSettingsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_public(db, project_id)


@router.delete("", status_code=204)
def reset_illustration_settings(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_access(project_id, current_user, db)
    row = find_row(db, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Aucun réglage pour ce périmètre")
    db.delete(row)
    db.commit()
    return None


@router.post("/preview", response_model=IllustrationPreviewResult)
def preview_illustration(
    data: IllustrationPreviewRequest | None = None,
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Génère UNE image d'essai avec les réglages saisis (non enregistrés).
    L'image est renvoyée en data URL et n'est pas stockée ; son coût est
    tracé dans ai.usage_events (agent image_generator)."""
    _ensure_access(project_id, current_user, db)
    data = data or IllustrationPreviewRequest()
    try:
        cfg = IllustrationConfig(mode="ai", **normalize_config(data.config.model_dump(exclude_none=True)))
    except IllustrationSettingsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    provider = get_image_provider(db, project_id, cfg.model)
    if provider is None:
        raise HTTPException(
            status_code=422,
            detail="Aucune clé OpenRouter configurée : ajoutez-la dans Paramètres → Providers IA.",
        )
    prompt = compose_image_prompt((data.subject or "").strip() or PREVIEW_SUBJECT, cfg)

    from app.services.seo.illustration_service import IMAGE_AGENT_KEY, log_usage
    from app.services.storage_service import optimize_image

    start = time.perf_counter()
    try:
        image = provider.generate(prompt)
    except ImageGenerationError as exc:
        log_usage(
            db, agent_key=IMAGE_AGENT_KEY, provider_code="openrouter", model=cfg.model, project_id=project_id,
            article_id=None, duration_ms=int((time.perf_counter() - start) * 1000), estimated_cost=None,
            error=str(exc)[:500],
        )
        raise HTTPException(status_code=502, detail=f"Génération impossible : {exc}") from exc
    cost = image.cost_usd if image.cost_usd is not None else approx_cost_usd(image.model)
    log_usage(
        db, agent_key=IMAGE_AGENT_KEY, provider_code="openrouter", model=image.model, project_id=project_id,
        article_id=None, duration_ms=int((time.perf_counter() - start) * 1000), estimated_cost=cost,
        actual_cost=image.cost_usd,
    )
    payload, mime, _w, _h = optimize_image(image.data, image.mime_type)
    return IllustrationPreviewResult(
        image_data_url=f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}",
        prompt=prompt,
        model=image.model,
        cost_usd=cost,
    )
