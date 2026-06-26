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
    sub_niche: Optional[str] = None
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
    seo_review_json: Optional[dict] = None
    project_context_json: Optional[dict] = None
    category_strategy_json: Optional[dict] = None
    idea_discovery_json: Optional[dict] = None
    intent_analysis_json: Optional[dict] = None
    research_brief_json: Optional[dict] = None
    keyword_brief_json: Optional[dict] = None
    cannibalization_check_json: Optional[dict] = None
    editorial_angle_json: Optional[dict] = None
    outline_json: Optional[str] = None
    image_plan_json: Optional[dict] = None
    image_sources_json: Optional[dict] = None
    callout_plan_json: Optional[dict] = None
    language_quality_report_json: Optional[dict] = None
    originality_report_json: Optional[dict] = None
    humanization_report_json: Optional[dict] = None
    eeat_checklist_json: Optional[dict] = None
    editorial_quality_report_json: Optional[dict] = None
    seo_final_checklist_json: Optional[dict] = None
    generation_report_json: Optional[dict] = None
    sources_json: Optional[dict] = None
    serp_analysis_json: Optional[dict] = None
    extracted_sources_json: Optional[dict] = None
    content_gap_json: Optional[dict] = None
    source_quality_report_json: Optional[dict] = None
    evidence_pack_json: Optional[dict] = None
    style_guide_json: Optional[dict] = None
    cannibalization_outline_json: Optional[dict] = None
    claims_json: Optional[dict] = None
    fact_check_report_json: Optional[dict] = None
    estimated_cost_json: Optional[dict] = None
    geo_optimization_json: Optional[dict] = None
    structured_data_json: Optional[dict] = None
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    featured: bool = False
    latest_analysis: Optional[AnalysisBrief]
    created_at: datetime
    updated_at: datetime
    published_content: Optional[str] = None
    published_title: Optional[str] = None
    published_excerpt: Optional[str] = None
    published_meta_description: Optional[str] = None
    published_cover_image_url: Optional[str] = None
    published_faq_json: Optional[str] = None
    published_callouts_json: Optional[str] = None
    has_draft_changes: Optional[bool] = None


class AutosaveRequest(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    keyword: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    cover_image_url: Optional[str] = None
    faq_json: Optional[str] = None
    callouts_json: Optional[str] = None
    internal_links_json: Optional[str] = None
    external_links_json: Optional[str] = None
    content_blocks_json: Optional[str] = None
    category_id: Optional[str] = None
    sub_niche: Optional[str] = None
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    featured: Optional[bool] = None


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
    sub_niche: Optional[str] = None
    featured: bool = False
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
