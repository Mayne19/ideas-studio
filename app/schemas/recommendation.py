from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RecommendationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    article_id: str | None
    type: str
    priority: int
    reason: str
    suggestion: str
    status: str
    created_at: datetime
    updated_at: datetime


class RecommendationStatusUpdate(BaseModel):
    status: str
