from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.traffic_event import TrafficEvent
from app.schemas.traffic import TrafficCollect
from app.core.utils import detect_device_from_user_agent, detect_browser_from_user_agent, hash_visitor


def collect_traffic_event(
    db: Session,
    data: TrafficCollect,
    client_ip: str,
) -> TrafficEvent:
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")
    if project.public_tracking_key != data.tracking_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Invalid tracking key")

    ua = data.user_agent or ""
    device = detect_device_from_user_agent(ua)
    browser = detect_browser_from_user_agent(ua)
    visitor_hash = hash_visitor(client_ip, ua)

    event = TrafficEvent(
        project_id=data.project_id,
        url=data.url,
        path=data.path,
        referrer=data.referrer,
        device=device,
        browser=browser,
        visitor_hash=visitor_hash,
        user_agent=ua or None,
    )
    db.add(event)

    now = datetime.now(timezone.utc)
    if project.status == "not_connected":
        project.status = "connected"
        project.connected_at = now
    project.last_seen_at = now

    db.commit()
    db.refresh(event)
    return event
