from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ArticleCreate(BaseModel):
    title: str
    category_id: Optional[str] = None
    sub_niche: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    keyword: Optional[str] = None
    search_intent: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    priority: int = 0
    is_featured: bool = False
    author_name: Optional[str] = None


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    category_id: Optional[str] = None
    sub_niche: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    keyword: Optional[str] = None
    search_intent: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    faq: Optional[list] = None
    callouts: Optional[list] = None
    rejection_reason: Optional[str] = None
    rejection_note: Optional[str] = None
    priority: Optional[int] = None
    is_featured: Optional[bool] = None
    author_name: Optional[str] = None
    target_word_count: Optional[int] = None
    content_format: Optional[str] = None  # short|medium|long|pillar


class ArticleScheduleRequest(BaseModel):
    scheduled_at: datetime


class ArticlePublic(BaseModel):
    id: str
    project_id: str
    category_id: Optional[str] = None
    sub_niche: Optional[str] = None
    title: str
    slug: str
    content: Optional[str] = None
    excerpt: Optional[str] = None
    status: int
    keyword: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    word_count: int = 0
    priority: int = 0
    is_featured: bool = False
    seo_score: Optional[float] = None
    readability_score: Optional[float] = None
    quality_score: Optional[float] = None
    eeat_score: Optional[float] = None
    geo_score: Optional[float] = None
    global_score: Optional[float] = None
    global_score_valid: Optional[bool] = None
    is_validable: Optional[bool] = None
    validation_reasons: list[str] = []
    critical_warnings: list[dict] = []
    published_at: Optional[datetime] = None
    scheduled_for: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    target_word_count: Optional[int] = None
    content_format: Optional[str] = None

    angle: Optional[str] = None
    search_intent: Optional[str] = None
    opportunity_score: Optional[float] = None
    audience: Optional[str] = None
    rejection_reason: Optional[str] = None
    rejection_note: Optional[str] = None

    has_draft_changes: bool = False


PromoteResponse = ArticlePublic


class BulkValidateRequest(BaseModel):
    article_ids: list[str]


class BulkValidateByScoreRequest(BaseModel):
    min_score: int
    statuses: list[int] = [20, 30]


class BlockedArticleInfo(BaseModel):
    article_id: str
    title: str
    reasons: list[str]


class BulkValidateResponse(BaseModel):
    validated_count: int
    blocked_count: int
    scheduled_count: int
    not_found_count: int = 0
    not_found_ids: list[str] = []
    blocked_articles: list[BlockedArticleInfo] = []


class BulkValidateByScoreResponse(BulkValidateResponse):
    score_threshold_applied: int
    total_eligible: int


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
    excerpt: Optional[str] = None
    content: Optional[str] = None
    category: Optional[CategoryBrief] = None
    category_slug: Optional[str] = None
    category_color: Optional[str] = None
    sub_niche: Optional[str] = None
    is_featured: bool = False
    main_keyword: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    faq: list = []
    callouts: list = []
    published_at: Optional[datetime] = None
    updated_at: datetime
    has_draft_changes: Optional[bool] = None
