from datetime import datetime
from pydantic import BaseModel


class SeoIssueSchema(BaseModel):
    type: str
    category: str       # seo | readability | quality | eeat
    severity: str       # info | warning | critical
    message: str
    suggestion: str
    section: str
    auto_fix_available: bool = False


class SeoAnalysisResponse(BaseModel):
    id: str
    article_id: str
    project_id: str
    seo_score: float
    readability_score: float
    quality_score: float
    eeat_score: float
    readiness_status: str
    issues: list[SeoIssueSchema]
    suggestions: list[str]
    created_at: datetime


class CriticalWarningSchema(BaseModel):
    type: str
    severity: str
    message: str


class ReadyCheckResponse(BaseModel):
    article_id: str
    readiness_status: str
    seo_score: float
    readability_score: float
    quality_score: float
    eeat_score: float
    global_score: float | None = None
    global_score_valid: bool | None = None
    blocking_issues: list[SeoIssueSchema]
    critical_warnings: list[CriticalWarningSchema] = []
    can_publish: bool


class ArticleEditorUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    content: str | None = None
    excerpt: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    cover_image_url: str | None = None
    faq_json: str | None = None
    callouts_json: str | None = None
    internal_links_json: str | None = None
    external_links_json: str | None = None
    content_blocks_json: str | None = None
    category_id: str | None = None
