from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ArticleCreate(BaseModel):
    title: str
    category_id: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    keyword: Optional[str] = None
    secondary_keywords_json: Optional[str] = None
    audience: Optional[str] = None
    angle: Optional[str] = None
    search_intent: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    cover_image_url: Optional[str] = None
    priority: int = 0


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    category_id: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    keyword: Optional[str] = None
    secondary_keywords_json: Optional[str] = None
    audience: Optional[str] = None
    angle: Optional[str] = None
    search_intent: Optional[str] = None
    outline_json: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    cover_image_url: Optional[str] = None
    faq_json: Optional[str] = None
    callouts_json: Optional[str] = None
    internal_links_json: Optional[str] = None
    external_links_json: Optional[str] = None
    rejection_reason: Optional[str] = None
    rejection_note: Optional[str] = None
    priority: Optional[int] = None


class ArticleScheduleRequest(BaseModel):
    scheduled_at: datetime


class ArticlePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    category_id: Optional[str]
    title: str
    slug: str
    content: Optional[str]
    excerpt: Optional[str]
    status: str
    keyword: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]
    cover_image_url: Optional[str]
    word_count: int
    priority: int
    seo_score: Optional[float]
    readability_score: Optional[float]
    quality_score: Optional[float]
    eeat_score: Optional[float]
    readiness_status: Optional[str]
    published_at: Optional[datetime]
    scheduled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# Response schema for the public blog API
class CategoryBrief(BaseModel):
    id: str
    name: str
    slug: str


class ArticlePublicApiResponse(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: Optional[str]
    content: Optional[str]
    category: Optional[CategoryBrief]
    meta_title: Optional[str]
    meta_description: Optional[str]
    cover_image_url: Optional[str]
    published_at: Optional[datetime]
    updated_at: datetime
