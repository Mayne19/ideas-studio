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
    author_name: Optional[str] = None


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
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None


class ArticleScheduleRequest(BaseModel):
    scheduled_at: datetime


class PromoteResponse(BaseModel):
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
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    updated_at: datetime
    revalidated: bool = False


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
    seo_review_json: Optional[dict] = None
    generation_report_json: Optional[dict] = None
    published_at: Optional[datetime]
    scheduled_at: Optional[datetime]
    created_at: datetime
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    updated_at: datetime

    # Extended fields
    estimated_cost_json: Optional[dict] = None
    actual_cost_json: Optional[dict] = None
    geo_optimization_json: Optional[dict] = None


# Response schema for the public blog API
class CategoryBrief(BaseModel):
    id: str
    name: str
    slug: str
    color: Optional[str] = None


class ArticlePublicApiResponse(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: Optional[str]
    content: Optional[str]
    category: Optional[CategoryBrief]
    category_slug: Optional[str] = None
    category_color: Optional[str] = None
    main_keyword: Optional[str] = None
    meta_title: Optional[str]
    meta_description: Optional[str]
    cover_image_url: Optional[str]
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    faq_json: Optional[str] = None
    callouts_json: Optional[str] = None
    published_at: Optional[datetime]
    updated_at: datetime
    has_draft_changes: Optional[bool] = None
