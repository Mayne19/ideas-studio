from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.core import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/projects/{project_id}", tags=["analytics"])


@router.get("/analytics/ga4")
def get_ga4_analytics(
    project_id: str,
    start_date: str = Query(default="30daysAgo"),
    end_date: str = Query(default="today"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retourne les données GA4 pour la page Analytics."""
    from app.services.ga4_service import get_full_report
    return get_full_report(start_date, end_date)
