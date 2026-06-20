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
    public_site_url: Optional[str] = None
    revalidate_url: Optional[str] = None
    revalidate_secret: Optional[str] = None


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
    public_site_url: Optional[str] = None
    revalidate_url: Optional[str] = None
    revalidate_secret_configured: bool = False
    last_revalidated_at: Optional[datetime] = None
    last_revalidate_status: Optional[str] = None
    last_revalidate_error: Optional[str] = None
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
    public_site_url: Optional[str] = None
    revalidate_url: Optional[str] = None
    revalidate_secret_configured: bool = False
    last_revalidated_at: Optional[datetime] = None
    last_revalidate_status: Optional[str] = None
    last_revalidate_error: Optional[str] = None
