import json
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_project_member
from app.models.project_member import ProjectMember
from app.services.activity_service import get_project_activity

router = APIRouter(tags=["activity"])


@router.get("/projects/{project_id}/activity")
def list_activity(
    project_id: str,
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    logs = get_project_activity(db, project_id, limit=limit, offset=offset, action=action)
    return [
        {
            "id": log.id,
            "project_id": log.project_id,
            "user_id": log.user_id,
            "user_name": log.user_name,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "description": log.description,
            "metadata": json.loads(log.metadata_json) if log.metadata_json else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
