from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CommentCreate(BaseModel):
    text: str
    selected_text: Optional[str] = None
    parent_id: Optional[str] = None


class CommentUpdate(BaseModel):
    resolved: bool


class CommentPublic(BaseModel):
    id: str
    article_id: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    parent_id: Optional[str] = None
    text: str
    selected_text: Optional[str] = None
    resolved: bool
    created_at: datetime
