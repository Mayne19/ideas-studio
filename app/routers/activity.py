from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import MemberView, get_project_member
from app.services.activity_service import get_project_activity

router = APIRouter(tags=["activity"])


@router.get("/projects/{project_id}/activity")
def list_activity(
    project_id: str,
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    member: MemberView = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    logs = get_project_activity(db, project_id, limit=limit, offset=offset, action=action)
    return [
        {
            "id": log.id,
            "project_id": log.project_id,
            "user_id": log.actor_id,
            "user_name": (log.context or {}).get("user_name"),
            "action": log.action,
            "resource_type": (log.context or {}).get("resource_type"),
            "resource_id": (log.context or {}).get("resource_id"),
            "description": log.message,
            "metadata": log.context or None,
            "created_at": log.occurred_at.isoformat() if log.occurred_at else None,
        }
        for log in logs
    ]
