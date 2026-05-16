from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AnalysisBrief(BaseModel):
    seo_score: float
    readability_score: float
    quality_score: float
    eeat_score: float
    readiness_status: str
    created_at: datetime


class EditorData(BaseModel):
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
    faq_json: Optional[str]
    callouts_json: Optional[str]
    internal_links_json: Optional[str]
    external_links_json: Optional[str]
    content_blocks_json: Optional[str]
    word_count: int
    seo_score: Optional[float]
    readability_score: Optional[float]
    quality_score: Optional[float]
    eeat_score: Optional[float]
    readiness_status: Optional[str]
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    latest_analysis: Optional[AnalysisBrief]
    created_at: datetime
    updated_at: datetime


class AutosaveRequest(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    cover_image_url: Optional[str] = None
    faq_json: Optional[str] = None
    callouts_json: Optional[str] = None
    internal_links_json: Optional[str] = None
    external_links_json: Optional[str] = None
    content_blocks_json: Optional[str] = None
    category_id: Optional[str] = None
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None


class AutosaveResponse(BaseModel):
    id: str
    word_count: int
    updated: bool
    version_created: bool
    updated_at: datetime


class PreviewResponse(BaseModel):
    id: str
    title: str
    slug: str
    content: Optional[str]
    excerpt: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]
    cover_image_url: Optional[str]
    faq_json: Optional[str]
    callouts_json: Optional[str]
    internal_links_json: Optional[str]
    external_links_json: Optional[str]
    content_blocks_json: Optional[str]
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    status: str


class VersionPublic(BaseModel):
    id: str
    article_id: str
    project_id: str
    title: str
    slug: str
    version_number: int
    version_type: str
    created_by: Optional[str]
    created_at: datetime
