from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    language: Optional[str] = None
    country_target: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    language: Optional[str] = None
    country_target: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None


class ProjectPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    domain: Optional[str]
    language: Optional[str]
    country_target: Optional[str]
    audience: Optional[str]
    tone: Optional[str]
    status: str
    public_tracking_key: str
    connected_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ProjectConnectInfo(BaseModel):
    project_id: str
    domain: Optional[str]
    status: str
    public_tracking_key: str
    secret_api_key_masked: str
    connected_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    snippet: str
    public_api_endpoints: dict
