from pydantic import BaseModel
from typing import Literal


class IdeaGenerateRequest(BaseModel):
    context_hint: str | None = None
    preferred_title: str | None = None


class IdeaGenerateResponse(BaseModel):
    id: str
    title: str
    keyword: str | None
    angle: str | None
    search_intent: str | None
    audience: str | None
    opportunity_score: float | None
    status: str

    model_config = {"from_attributes": True}


class IdeaRejectRequest(BaseModel):
    rejection_reason: str | None = None
    rejection_note: str | None = None


class IdeaPriorityRequest(BaseModel):
    priority: int = 1


class LaunchRequest(BaseModel):
    mode: Literal["idea_only", "full_article"] = "idea_only"
    dry_run: bool = False
