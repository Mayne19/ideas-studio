"""Schedule-aware front door for the local writer queue."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import require_project_role
from app.services.local_writer_service import writing_jobs
from app.services.writing_schedule_service import queue_capacity

router = APIRouter(prefix="/projects/{project_id}/local-writer", tags=["local_writer"])

_WRITE_ROLES = ("owner", "admin", "editor")


class WriterJob(BaseModel):
    article_id: str
    subject: str
    keyword: str | None = None
    context: str | None = None
    audience: str | None = None
    angle: str | None = None
    comment: str | None = None


@router.get("/jobs", response_model=list[WriterJob])
def list_scheduled_jobs(
    project_id: str,
    db: Session = Depends(get_db),
    _member=Depends(require_project_role(*_WRITE_ROLES)),
):
    capacity = queue_capacity(db, project_id)
    if capacity <= 0:
        return []
    return writing_jobs(db, project_id)[:capacity]
