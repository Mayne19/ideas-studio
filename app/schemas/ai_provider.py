from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AIProviderCreate(BaseModel):
    provider: str
    label: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    is_default: bool = False
    enabled: bool = True


class AIProviderUpdate(BaseModel):
    label: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None


class AIProviderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider: str
    label: str
    api_key_configured: bool = False
    model: Optional[str] = None
    base_url: Optional[str] = None
    is_default: bool
    enabled: bool
    last_test_status: Optional[str] = None
    last_test_error: Optional[str] = None
    last_tested_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AIProviderTestResult(BaseModel):
    provider: str
    status: str
    message: Optional[str] = None
    model: Optional[str] = None
