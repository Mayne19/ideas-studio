from typing import Optional
from pydantic import BaseModel


class TrafficCollect(BaseModel):
    project_id: str
    tracking_key: str
    url: str
    path: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
