from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AIProviderCreate(BaseModel):
    provider: str
    label: str
    project_id: Optional[str] = None
    api_key: Optional[str] = None


class AIProviderUpdate(BaseModel):
    api_key: Optional[str] = None


class AIProviderPublic(BaseModel):
    id: str
    project_id: Optional[str] = None
    provider: str
    label: str
    api_key_configured: bool = False
    base_url: Optional[str] = None
    last_test_status: Optional[str] = None
    last_test_error: Optional[str] = None
    last_tested_at: Optional[datetime] = None
    created_at: datetime


class AIProviderTestResult(BaseModel):
    provider: str
    status: str
    message: Optional[str] = None
    model: Optional[str] = None
