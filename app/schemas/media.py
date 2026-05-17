from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class MediaCreate(BaseModel):
    url: str
    filename: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    source: Optional[str] = None
    article_id: Optional[str] = None


class MediaUpdate(BaseModel):
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    source: Optional[str] = None
    article_id: Optional[str] = None


class MediaPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    article_id: Optional[str]
    url: str
    public_url: Optional[str] = None
    filename: str
    mime_type: Optional[str]
    size: Optional[int]
    alt_text: Optional[str]
    caption: Optional[str]
    source: Optional[str]
    created_at: datetime
    updated_at: datetime
