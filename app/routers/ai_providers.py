import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.core import User
from app.models.ai import Provider, ProviderCredential
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate, AIProviderPublic, AIProviderTestResult
from app.core.security import decrypt_secret, encrypt_secret
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/ai-providers", tags=["ai_providers"])


def _ensure_platform_admin(current_user: User) -> None:
    if current_user.is_staff:
        return
    raise HTTPException(status_code=403, detail="Admin access required")


def _ensure_provider_access(project_id: str | None, current_user: User, db: Session) -> None:
    if not project_id:
        _ensure_platform_admin(current_user)
        return
    if current_user.is_staff:
        return
    member = get_member_for_project(db, current_user.id, project_id)
    if not member or member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Project admin access required")


def _to_public(credential: ProviderCredential, provider_row: Provider) -> AIProviderPublic:
    return AIProviderPublic(
        id=credential.id,
        project_id=credential.project_id,
        provider=provider_row.code,
        label=provider_row.label,
        api_key_configured=bool(credential.secret_ref),
        base_url=provider_row.base_url,
        last_test_status="connected" if credential.last_test_ok else ("error" if credential.last_test_ok is False else None),
        last_test_error=None,
        last_tested_at=credential.last_test_at,
        created_at=credential.created_at,
    )


@router.get("", response_model=list[AIProviderPublic])
def list_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    project_id: str | None = None,
):
    _ensure_provider_access(project_id, current_user, db)
    query = select(ProviderCredential)
    if project_id:
        query = query.where(ProviderCredential.project_id == project_id)
    else:
        query = query.where(ProviderCredential.project_id.is_(None))
    credentials = db.execute(query).scalars().all()
    result = []
    for credential in credentials:
        provider_row = db.get(Provider, credential.provider_id)
        if provider_row:
            result.append(_to_public(credential, provider_row))
    result.sort(key=lambda p: p.provider)
    return result


@router.post("", response_model=AIProviderPublic, status_code=201)
def create_provider(
    data: AIProviderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_provider_access(data.project_id, current_user, db)
    provider_row = db.execute(select(Provider).where(Provider.code == data.provider)).scalar_one_or_none()
    if not provider_row:
        raise HTTPException(status_code=404, detail=f"Provider '{data.provider}' not found in catalog")

    existing = db.execute(
        select(ProviderCredential).where(
            ProviderCredential.project_id == data.project_id,
            ProviderCredential.provider_id == provider_row.id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Provider '{data.provider}' already configured for this project")

    credential = ProviderCredential(
        provider_id=provider_row.id,
        project_id=data.project_id,
        secret_ref=encrypt_secret(data.api_key) or "",
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return _to_public(credential, provider_row)


@router.patch("/{provider_id}", response_model=AIProviderPublic)
def update_provider(
    provider_id: str,
    data: AIProviderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = db.get(ProviderCredential, provider_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Provider not found")
    _ensure_provider_access(credential.project_id, current_user, db)

    if data.api_key is not None:
        credential.secret_ref = encrypt_secret(data.api_key) or ""

    db.commit()
    db.refresh(credential)
    provider_row = db.get(Provider, credential.provider_id)
    return _to_public(credential, provider_row)


@router.delete("/{provider_id}", status_code=204)
def delete_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = db.get(ProviderCredential, provider_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Provider not found")
    _ensure_provider_access(credential.project_id, current_user, db)
    db.delete(credential)
    db.commit()
    return None


@router.post("/{provider_id}/test", response_model=AIProviderTestResult)
def test_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = db.get(ProviderCredential, provider_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Provider not found")
    _ensure_provider_access(credential.project_id, current_user, db)
    provider_row = db.get(Provider, credential.provider_id)

    api_key = decrypt_secret(credential.secret_ref)
    if not api_key and provider_row.code != "ollama":
        credential.last_test_ok = False
        credential.last_test_at = datetime.now(timezone.utc)
        db.commit()
        return AIProviderTestResult(provider=provider_row.code, status="error", message="Aucune clé API configurée")

    try:
        from app.services.providers.provider_config import ResolvedProviderConfig
        from app.services.providers.llm_provider import build_provider_from_config

        shim = ResolvedProviderConfig(id=credential.id, provider=provider_row.code, model=None, base_url=provider_row.base_url, api_key_encrypted=credential.secret_ref)
        test_prov = build_provider_from_config(shim)
        if test_prov is None:
            credential.last_test_ok = False
            credential.last_test_at = datetime.now(timezone.utc)
            db.commit()
            return AIProviderTestResult(provider=provider_row.code, status="error", message=f"Provider '{provider_row.code}' non supporté")
        available = test_prov.is_available()

        credential.last_test_ok = available
        credential.last_test_at = datetime.now(timezone.utc)
        db.commit()

        return AIProviderTestResult(
            provider=provider_row.code,
            status="connected" if available else "error",
            message=None if available else "API a retourné une erreur (clé invalide ?)",
            model=test_prov.model_name,
        )
    except Exception as exc:
        credential.last_test_ok = False
        credential.last_test_at = datetime.now(timezone.utc)
        db.commit()
        return AIProviderTestResult(provider=provider_row.code, status="error", message=str(exc))


@router.get("/default")
def get_default_provider(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    project_id: str | None = None,
):
    _ensure_provider_access(project_id, current_user, db)
    from app.services.providers.provider_config import resolve_default_provider

    config = resolve_default_provider(db, project_id)
    if config:
        return {
            "provider": config.provider,
            "model": config.model,
            "configured": bool(config.api_key_encrypted),
            "enabled": True,
        }
    return {
        "provider": settings.DEFAULT_LLM_PROVIDER,
        "model": getattr(settings, f"{settings.DEFAULT_LLM_PROVIDER.upper()}_MODEL", None),
        "configured": False,
        "enabled": True,
        "source": "env",
    }


@router.get("/{provider_id}", response_model=AIProviderPublic)
def get_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credential = db.get(ProviderCredential, provider_id)
    if not credential:
        raise HTTPException(status_code=404, detail="Provider not found")
    _ensure_provider_access(credential.project_id, current_user, db)
    provider_row = db.get(Provider, credential.provider_id)
    return _to_public(credential, provider_row)
