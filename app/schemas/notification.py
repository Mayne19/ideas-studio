from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class NotificationPublic(BaseModel):
    id: str
    project_id: str
    user_id: Optional[str] = None
    type: str
    title: str
    message: str
    level: str
    link: Optional[str] = None
    read_at: Optional[datetime] = None
    created_at: datetime
