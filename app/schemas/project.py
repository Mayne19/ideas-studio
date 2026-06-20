from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    language: Optional[str] = None
    country_target: Optional[str] = None
    timezone: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    reader_level: Optional[str] = None
    writing_style: Optional[str] = None
    editorial_goal: Optional[str] = None
    value_proposition: Optional[str] = None
    allowed_topics: Optional[str] = None
    forbidden_topics: Optional[str] = None
    words_to_avoid: Optional[str] = None
    average_target_length: Optional[str] = None
    preferred_formats: Optional[str] = None
    technical_level: Optional[str] = None
    seo_rules: Optional[str] = None
    geo_rules: Optional[str] = None
    source_guidelines: Optional[str] = None
    internal_linking_guidelines: Optional[str] = None
    external_linking_guidelines: Optional[str] = None
    style_examples: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    language: Optional[str] = None
    country_target: Optional[str] = None
    timezone: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    reader_level: Optional[str] = None
    writing_style: Optional[str] = None
    editorial_goal: Optional[str] = None
    value_proposition: Optional[str] = None
    allowed_topics: Optional[str] = None
    forbidden_topics: Optional[str] = None
    words_to_avoid: Optional[str] = None
    average_target_length: Optional[str] = None
    preferred_formats: Optional[str] = None
    technical_level: Optional[str] = None
    seo_rules: Optional[str] = None
    geo_rules: Optional[str] = None
    source_guidelines: Optional[str] = None
    internal_linking_guidelines: Optional[str] = None
    external_linking_guidelines: Optional[str] = None
    style_examples: Optional[str] = None
    public_site_url: Optional[str] = None
    revalidate_url: Optional[str] = None
    revalidate_secret: Optional[str] = None


class ProjectPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    domain: Optional[str]
    language: Optional[str]
    country_target: Optional[str]
    timezone: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    audience: Optional[str]
    tone: Optional[str]
    reader_level: Optional[str] = None
    writing_style: Optional[str] = None
    editorial_goal: Optional[str] = None
    value_proposition: Optional[str] = None
    allowed_topics: Optional[str] = None
    forbidden_topics: Optional[str] = None
    words_to_avoid: Optional[str] = None
    average_target_length: Optional[str] = None
    preferred_formats: Optional[str] = None
    technical_level: Optional[str] = None
    seo_rules: Optional[str] = None
    geo_rules: Optional[str] = None
    source_guidelines: Optional[str] = None
    internal_linking_guidelines: Optional[str] = None
    external_linking_guidelines: Optional[str] = None
    style_examples: Optional[str] = None
    status: str
    public_tracking_key: str
    connected_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    public_site_url: Optional[str] = None
    revalidate_url: Optional[str] = None
    revalidate_secret_configured: bool = False
    last_revalidated_at: Optional[datetime] = None
    last_revalidate_status: Optional[str] = None
    last_revalidate_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ProjectConnectInfo(BaseModel):
    project_id: str
    domain: Optional[str]
    status: str
    public_tracking_key: str
    secret_api_key_masked: str
    connected_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    snippet: str
    public_api_endpoints: dict
    public_site_url: Optional[str] = None
    revalidate_url: Optional[str] = None
    revalidate_secret_configured: bool = False
    last_revalidated_at: Optional[datetime] = None
    last_revalidate_status: Optional[str] = None
    last_revalidate_error: Optional[str] = None
