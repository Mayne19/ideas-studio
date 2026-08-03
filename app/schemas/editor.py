from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AnalysisBrief(BaseModel):
    seo_score: Optional[float] = None
    readability_score: Optional[float] = None
    quality_score: Optional[float] = None
    eeat_score: Optional[float] = None
    geo_score: Optional[float] = None
    global_score: Optional[float] = None
    created_at: datetime


class EditorData(BaseModel):
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
    faq: list = []
    callouts: list = []
    word_count: int = 0
    # Toutes les sorties agents (project_context, outline, eeat_checklist, ...)
    # indexées par agent_key — remplace les ~30 colonnes *_json de l'ancien
    # modèle, voir ai.artifacts.
    artifacts: dict[str, dict] = {}
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    is_featured: bool = False
    latest_analysis: Optional[AnalysisBrief] = None
    created_at: datetime
    updated_at: datetime
    published_title: Optional[str] = None
    published_content: Optional[str] = None
    published_excerpt: Optional[str] = None
    published_meta_description: Optional[str] = None
    has_draft_changes: bool = False


class AutosaveRequest(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    keyword: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    faq: Optional[list] = None
    callouts: Optional[list] = None
    category_id: Optional[str] = None
    sub_niche: Optional[str] = None
    author_name: Optional[str] = None
    is_featured: Optional[bool] = None


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
    content: Optional[str] = None
    excerpt: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    sub_niche: Optional[str] = None
    is_featured: bool = False
    faq: list = []
    callouts: list = []
    author_name: Optional[str] = None
    reading_time_minutes: Optional[int] = None
    status: int


class VersionPublic(BaseModel):
    id: str
    article_id: str
    project_id: str
    title: str
    revision_no: int
    source: str
    created_by: Optional[str] = None
    created_at: datetime
