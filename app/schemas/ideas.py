from pydantic import BaseModel
from typing import Literal


class IdeaGenerateRequest(BaseModel):
    context_hint: str | None = None
    preferred_title: str | None = None
    keyword: str | None = None
    category_id: str | None = None
    audience: str | None = None
    angle: str | None = None
    search_intent: str | None = None
    include_faq: bool | None = None
    include_callouts: bool | None = None


class IdeaGenerateResponse(BaseModel):
    id: str
    title: str
    keyword: str | None
    category_id: str | None = None
    angle: str | None
    search_intent: str | None
    audience: str | None
    opportunity_score: float | None
    status: str
    provider_name: str | None = None
    model_name: str | None = None

    model_config = {"from_attributes": True}


class IdeaRejectRequest(BaseModel):
    rejection_reason: str | None = None
    rejection_note: str | None = None


class IdeaPriorityRequest(BaseModel):
    priority: int = 1


class LaunchRequest(BaseModel):
    mode: Literal["idea_only", "full_article"] = "idea_only"
    dry_run: bool = False
    context_hint: str | None = None
    preferred_title: str | None = None
    keyword: str | None = None
    category_id: str | None = None
    audience: str | None = None
    angle: str | None = None
    search_intent: str | None = None
    include_faq: bool | None = None
    include_callouts: bool | None = None
