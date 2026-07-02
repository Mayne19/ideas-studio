import ipaddress
import json
import logging
from typing import Optional
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_project_member, require_project_role
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookPublic
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


def _validate_webhook_url(url: str) -> None:
    """Bloque les URLs internes et non-HTTPS pour prévenir les requêtes vers le réseau interne."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="URL webhook invalide")

    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Les webhooks doivent utiliser HTTPS")

    hostname = parsed.hostname or ""
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise HTTPException(status_code=400, detail="URL webhook pointe vers une adresse réseau interne")
    except ValueError:
        pass  # C'est un hostname DNS, pas une IP — OK

    blocked_hosts = {"localhost", "metadata.google.internal"}
    if hostname.lower() in blocked_hosts:
        raise HTTPException(status_code=400, detail="URL webhook non autorisée")


@router.get("/projects/{project_id}/webhooks", response_model=list[WebhookPublic])
def list_webhooks(
    project_id: str,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    hooks = db.query(Webhook).filter(Webhook.project_id == project_id).all()
    return [_webhook_to_public(h) for h in hooks]


@router.post("/projects/{project_id}/webhooks", response_model=WebhookPublic, status_code=201)
def create_webhook(
    project_id: str,
    data: WebhookCreate,
    member: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    _validate_webhook_url(data.url)
    hook = Webhook(
        project_id=project_id,
        name=data.name,
        url=data.url,
        events=json.dumps(data.events),
    )
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return _webhook_to_public(hook)


@router.patch("/projects/{project_id}/webhooks/{webhook_id}", response_model=WebhookPublic)
def update_webhook(
    project_id: str,
    webhook_id: str,
    data: WebhookUpdate,
    member: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    hook = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.project_id == project_id).first()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if data.name is not None:
        hook.name = data.name
    if data.url is not None:
        _validate_webhook_url(data.url)
        hook.url = data.url
    if data.events is not None:
        hook.events = json.dumps(data.events)
    if data.enabled is not None:
        hook.enabled = data.enabled
    hook.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(hook)
    return _webhook_to_public(hook)


@router.delete("/projects/{project_id}/webhooks/{webhook_id}", status_code=204)
def delete_webhook(
    project_id: str,
    webhook_id: str,
    member: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    hook = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.project_id == project_id).first()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(hook)
    db.commit()
    return None


@router.post("/projects/{project_id}/webhooks/{webhook_id}/test")
def test_webhook(
    project_id: str,
    webhook_id: str,
    member: ProjectMember = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    hook = db.query(Webhook).filter(Webhook.id == webhook_id, Webhook.project_id == project_id).first()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    payload = {
        "event": "test",
        "project_id": project_id,
        "message": "Ceci est un test de votre webhook Ideas Studio.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                hook.url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-IdeasStudio-Signature": hook.sign_payload(json.dumps(payload)),
                    "X-IdeasStudio-Event": "test",
                },
            )
            hook.last_status = "success" if resp.is_success else f"HTTP {resp.status_code}"
            hook.last_triggered_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "ok" if resp.is_success else "error", "status_code": resp.status_code}
    except Exception as exc:
        hook.last_status = "error"
        hook.last_error = str(exc)
        hook.last_triggered_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Webhook test failed: {exc}")


def _webhook_to_public(hook: Webhook) -> dict:
    return {
        "id": hook.id,
        "project_id": hook.project_id,
        "name": hook.name,
        "url": hook.url,
        "events": json.loads(hook.events) if hook.events else [],
        "enabled": hook.enabled,
        "last_triggered_at": hook.last_triggered_at,
        "last_status": hook.last_status,
        "created_at": hook.created_at,
        "updated_at": hook.updated_at,
    }


def trigger_webhooks(db: Session, project_id: str, event: str, data: dict):
    """Trigger all webhooks subscribed to a given event."""
    import json
    import httpx
    from datetime import datetime, timezone

    hooks = db.query(Webhook).filter(
        Webhook.project_id == project_id,
        Webhook.enabled == True,
    ).all()

    for hook in hooks:
        subscribed_events = json.loads(hook.events) if hook.events else []
        if event not in subscribed_events:
            continue

        payload = {
            "event": event,
            "project_id": project_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    hook.url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-IdeasStudio-Signature": hook.sign_payload(json.dumps(payload)),
                        "X-IdeasStudio-Event": event,
                    },
                )
                hook.last_status = "success" if resp.is_success else f"HTTP {resp.status_code}"
                hook.last_triggered_at = datetime.now(timezone.utc)
        except Exception as exc:
            hook.last_status = "error"
            hook.last_error = str(exc)
            hook.last_triggered_at = datetime.now(timezone.utc)
            logger.warning("Webhook %s failed for event %s: %s", hook.id, event, exc)

    db.commit()
