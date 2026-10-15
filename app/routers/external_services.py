"""Paramètres → Services externes : clés de recherche web et de banques
d'images, par projet (ou globales si project_id absent, staff uniquement).
Même modèle d'accès que /settings/ai-providers. Les clés ne sont jamais
renvoyées : seulement api_key_configured + 4 derniers caractères."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_member_for_project
from app.models.core import User
from app.schemas.external_service import (
    ExternalServiceProviderOption,
    ExternalServicePublic,
    ExternalServiceTestRequest,
    ExternalServiceTestResult,
    ExternalServiceUpsert,
)
from app.services.providers.external_services import (
    EXTERNAL_SERVICES,
    ExternalServiceConfigError,
    ServiceCredential,
    check_credential,
    effective_credential,
    find_row,
    is_valid_provider,
    mask_key,
    row_to_credential,
    upsert_credential,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/external-services", tags=["external_services"])


def _ensure_access(project_id: str | None, current_user: User, db: Session) -> None:
    if not project_id:
        if current_user.is_staff:
            return
        raise HTTPException(status_code=403, detail="Admin access required")
    if current_user.is_staff:
        return
    member = get_member_for_project(db, current_user.id, project_id)
    if not member or member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Project admin access required")


def _ensure_service(service: str) -> dict:
    meta = EXTERNAL_SERVICES.get(service)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Service '{service}' inconnu")
    return meta


def _to_public(db: Session, service: str, project_id: str | None) -> ExternalServicePublic:
    meta = EXTERNAL_SERVICES[service]
    row = find_row(db, service, project_id)
    stored = row_to_credential(row) if row is not None else None
    effective = effective_credential(db, service, project_id)
    test_status = None
    if row is not None and row.last_test_ok is not None:
        test_status = "connected" if row.last_test_ok else "error"
    return ExternalServicePublic(
        service=service,
        label=meta["label"],
        description=meta.get("description"),
        providers=[
            ExternalServiceProviderOption(code=code, label=p["label"], fields=p.get("fields", []), docs_url=p.get("docs_url"))
            for code, p in meta["providers"].items()
        ],
        id=row.id if row is not None else None,
        project_id=project_id,
        provider=row.provider if row is not None else None,
        api_key_configured=stored is not None,
        key_last4=mask_key(stored.api_key) if stored else None,
        config=dict(row.config or {}) if row is not None else {},
        last_test_status=test_status,
        last_test_error=row.last_test_error if row is not None else None,
        last_tested_at=row.last_test_at if row is not None else None,
        updated_at=row.updated_at if row is not None else None,
        effective_source=effective.source if effective else None,
        effective_provider=effective.provider if effective else None,
        effective_key_last4=mask_key(effective.api_key) if effective else None,
    )


@router.get("", response_model=list[ExternalServicePublic])
def list_external_services(
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_access(project_id, current_user, db)
    return [_to_public(db, service, project_id) for service in EXTERNAL_SERVICES]


@router.put("/{service}", response_model=ExternalServicePublic)
def upsert_external_service(
    service: str,
    data: ExternalServiceUpsert,
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_service(service)
    _ensure_access(project_id, current_user, db)
    try:
        upsert_credential(db, service, project_id, data.provider, data.api_key, data.config)
    except ExternalServiceConfigError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_public(db, service, project_id)


@router.delete("/{service}", status_code=204)
def delete_external_service(
    service: str,
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_service(service)
    _ensure_access(project_id, current_user, db)
    row = find_row(db, service, project_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Aucune configuration pour ce service")
    db.delete(row)
    db.commit()
    return None


@router.post("/{service}/test", response_model=ExternalServiceTestResult)
def test_external_service(
    service: str,
    data: ExternalServiceTestRequest | None = None,
    project_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sans corps : teste la clé enregistrée pour ce périmètre (ou, à défaut,
    celle réellement utilisée : globale ou variable d'environnement). Avec
    provider + api_key : teste la clé saisie avant enregistrement."""
    _ensure_service(service)
    _ensure_access(project_id, current_user, db)

    row = find_row(db, service, project_id)
    if data is not None and data.api_key:
        provider = data.provider or (row.provider if row is not None else None)
        if not provider or not is_valid_provider(service, provider):
            raise HTTPException(status_code=422, detail="Provider invalide")
        cred = ServiceCredential(service, provider, data.api_key.strip(), dict(data.config or {}), source="input")
        ok, message = check_credential(cred)
        return ExternalServiceTestResult(
            service=service, provider=provider, source="input",
            status="connected" if ok else "error", message=message,
        )

    cred = row_to_credential(row) if row is not None else effective_credential(db, service, project_id)
    if cred is None:
        if row is not None:
            row.last_test_ok = False
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_error = "Clé illisible — ressaisissez-la"
            db.commit()
            return ExternalServiceTestResult(service=service, provider=row.provider, status="error", message=row.last_test_error)
        return ExternalServiceTestResult(service=service, status="error", message="Aucune clé configurée")

    ok, message = check_credential(cred)
    if row is not None and cred.source in ("project", "global"):
        row.last_test_ok = ok
        row.last_test_at = datetime.now(timezone.utc)
        row.last_test_error = message
        db.commit()
    return ExternalServiceTestResult(
        service=service, provider=cred.provider, source=cred.source,
        status="connected" if ok else "error", message=message,
    )
