from datetime import datetime
from typing import Optional
from pydantic import BaseModel


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
    id: str
    project_id: str
    article_id: Optional[str] = None
    url: str
    public_url: Optional[str] = None
    filename: str
    mime_type: Optional[str] = None
    size: Optional[int] = None
    alt_text: Optional[str] = None
    caption: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime
