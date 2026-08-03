import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Project, ProjectCredential
from app.models.analytics import TrafficEvent
from app.models.reference import CredentialKind, ProjectStatus, set_project_status
from app.schemas.traffic import TrafficCollect
from app.core.utils import detect_device_from_user_agent, detect_browser_from_user_agent, hash_visitor


def _referrer_host(referrer: str | None) -> str | None:
    if not referrer:
        return None
    try:
        host = urlparse(referrer).netloc
        return host or None
    except ValueError:
        return None


def collect_traffic_event(
    db: Session,
    data: TrafficCollect,
    client_ip: str,
) -> TrafficEvent:
    project = db.get(Project, data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clé en clair côté client, comparée par digest SHA-256 côté serveur — jamais
    # de comparaison en clair contre la base (core.project_credentials.token_sha256).
    # Voir db/migration-v3/REPRENDRE-LA-MAIN.md §6 étape 4.
    key_hash = hashlib.sha256(data.tracking_key.encode("utf-8")).digest()
    credential = db.execute(
        select(ProjectCredential).where(
            ProjectCredential.project_id == data.project_id,
            ProjectCredential.kind == CredentialKind.TRACKING,
            ProjectCredential.token_sha256 == key_hash,
            ProjectCredential.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if not credential:
        raise HTTPException(status_code=403, detail="Invalid tracking key")

    ua = data.user_agent or ""
    device = detect_device_from_user_agent(ua)
    browser = detect_browser_from_user_agent(ua)
    visitor_hash = hash_visitor(client_ip, ua)

    event = TrafficEvent(
        project_id=data.project_id,
        path=data.path or urlparse(data.url).path or "/",
        referrer_host=_referrer_host(data.referrer),
        device=device,
        browser=browser,
        visitor_hash=visitor_hash,
    )
    db.add(event)

    if project.status_reason_id == ProjectStatus.NOT_CONNECTED:
        set_project_status(project, ProjectStatus.CONNECTED)
    credential.last_used_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(event)
    return event
