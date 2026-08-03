import hashlib
import hmac
import ipaddress
import logging
import secrets
from typing import Optional
from urllib.parse import urlparse
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decrypt_secret, encrypt_secret
from app.dependencies.auth import MemberView, get_project_member, require_project_role
from app.models.ops import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookCreate, WebhookUpdate, WebhookPublic
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


def _sign_payload(hook: Webhook, payload: str) -> str:
    secret = decrypt_secret(hook.secret_ref) or ""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


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


def _latest_delivery(db: Session, webhook_id: str) -> WebhookDelivery | None:
    return db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.delivered_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _webhook_to_public(db: Session, hook: Webhook) -> WebhookPublic:
    last = _latest_delivery(db, hook.id)
    last_status = None
    if last:
        last_status = "success" if last.status_code and 200 <= last.status_code < 300 else (f"HTTP {last.status_code}" if last.status_code else "error")
    return WebhookPublic(
        id=hook.id,
        project_id=hook.project_id,
        name=hook.name,
        url=hook.url,
        events=hook.events or [],
        enabled=hook.is_enabled,
        last_triggered_at=last.delivered_at if last else None,
        last_status=last_status,
        created_at=hook.created_at,
    )


@router.get("/projects/{project_id}/webhooks", response_model=list[WebhookPublic])
def list_webhooks(
    project_id: str,
    member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    hooks = db.execute(select(Webhook).where(Webhook.project_id == project_id)).scalars().all()
    return [_webhook_to_public(db, h) for h in hooks]


@router.post("/projects/{project_id}/webhooks", response_model=WebhookPublic, status_code=201)
def create_webhook(
    project_id: str,
    data: WebhookCreate,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    _validate_webhook_url(data.url)
    hook = Webhook(
        project_id=project_id,
        name=data.name,
        url=data.url,
        events=data.events,
        secret_ref=encrypt_secret(secrets.token_hex(32)) or "",
    )
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return _webhook_to_public(db, hook)


@router.patch("/projects/{project_id}/webhooks/{webhook_id}", response_model=WebhookPublic)
def update_webhook(
    project_id: str,
    webhook_id: str,
    data: WebhookUpdate,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    hook = db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.project_id == project_id)
    ).scalar_one_or_none()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if data.name is not None:
        hook.name = data.name
    if data.url is not None:
        _validate_webhook_url(data.url)
        hook.url = data.url
    if data.events is not None:
        hook.events = data.events
    if data.enabled is not None:
        hook.is_enabled = data.enabled
    db.commit()
    db.refresh(hook)
    return _webhook_to_public(db, hook)


@router.delete("/projects/{project_id}/webhooks/{webhook_id}", status_code=204)
def delete_webhook(
    project_id: str,
    webhook_id: str,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    hook = db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.project_id == project_id)
    ).scalar_one_or_none()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(hook)
    db.commit()
    return None


@router.post("/projects/{project_id}/webhooks/{webhook_id}/test")
def test_webhook(
    project_id: str,
    webhook_id: str,
    member: MemberView = Depends(require_project_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    import json

    hook = db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.project_id == project_id)
    ).scalar_one_or_none()
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")

    payload = {
        "event": "test",
        "project_id": project_id,
        "message": "Ceci est un test de votre webhook Ideas Studio.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload_json = json.dumps(payload)

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                hook.url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-IdeasStudio-Signature": _sign_payload(hook, payload_json),
                    "X-IdeasStudio-Event": "test",
                },
            )
            db.add(WebhookDelivery(webhook_id=hook.id, event="test", status_code=resp.status_code))
            db.commit()
            return {"status": "ok" if resp.is_success else "error", "status_code": resp.status_code}
    except Exception as exc:
        db.add(WebhookDelivery(webhook_id=hook.id, event="test", error=str(exc)))
        db.commit()
        raise HTTPException(status_code=502, detail=f"Webhook test failed: {exc}")


def trigger_webhooks(db: Session, project_id: str, event: str, data: dict):
    """Trigger all webhooks subscribed to a given event."""
    import json

    hooks = db.execute(
        select(Webhook).where(Webhook.project_id == project_id, Webhook.is_enabled.is_(True))
    ).scalars().all()

    for hook in hooks:
        if event not in (hook.events or []):
            continue

        payload = {
            "event": event,
            "project_id": project_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payload_json = json.dumps(payload)

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    hook.url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-IdeasStudio-Signature": _sign_payload(hook, payload_json),
                        "X-IdeasStudio-Event": event,
                    },
                )
                db.add(WebhookDelivery(webhook_id=hook.id, event=event, status_code=resp.status_code))
        except Exception as exc:
            db.add(WebhookDelivery(webhook_id=hook.id, event=event, error=str(exc)))
            logger.warning("Webhook %s failed for event %s: %s", hook.id, event, exc)

    db.commit()
