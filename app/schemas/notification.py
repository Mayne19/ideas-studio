from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class NotificationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    user_id: Optional[str]
    type: str
    title: str
    message: str
    level: str
    link: Optional[str]
    read_at: Optional[datetime]
    created_at: datetime
