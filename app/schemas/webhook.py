from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: list[str]


class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[list[str]] = None
    enabled: Optional[bool] = None


class WebhookPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    url: str
    events: list[str]
    enabled: bool
    last_triggered_at: Optional[datetime] = None
    last_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
