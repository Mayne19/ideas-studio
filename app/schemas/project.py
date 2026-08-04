from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    reader_level: Optional[str] = None
    writing_style: Optional[str] = None
    vertical: Optional[str] = None
    word_count_min: Optional[int] = None
    word_count_max: Optional[int] = None
    rules: Optional[dict] = None
    constraints: Optional[dict] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    reader_level: Optional[str] = None
    writing_style: Optional[str] = None
    vertical: Optional[str] = None
    word_count_min: Optional[int] = None
    word_count_max: Optional[int] = None
    rules: Optional[dict] = None
    constraints: Optional[dict] = None
    site_url: Optional[str] = None
    revalidate_url: Optional[str] = None


class ProjectPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: Optional[str] = None
    name: str
    domain: Optional[str] = None
    locale: str
    timezone: str
    audience: Optional[str] = None
    tone: Optional[str] = None
    reader_level: Optional[str] = None
    writing_style: Optional[str] = None
    vertical: Optional[str] = None
    word_count_min: Optional[int] = None
    word_count_max: Optional[int] = None
    status: int
    public_tracking_key_prefix: Optional[str] = None
    connected_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    public_site_url: Optional[str] = None
    revalidate_url: Optional[str] = None
    revalidate_configured: bool = False
    last_revalidated_at: Optional[datetime] = None
    last_revalidate_status: Optional[str] = None
    last_revalidate_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectConnectInfo(BaseModel):
    project_id: str
    domain: Optional[str] = None
    status: int
    public_tracking_key: Optional[str] = None
    secret_api_key_masked: Optional[str] = None
    connected_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    snippet: str
    public_api_endpoints: dict
    public_site_url: Optional[str] = None
    revalidate_url: Optional[str] = None
    revalidate_secret: Optional[str] = None
    revalidate_configured: bool = False
    last_revalidated_at: Optional[datetime] = None
    last_revalidate_status: Optional[str] = None
    last_revalidate_error: Optional[str] = None
