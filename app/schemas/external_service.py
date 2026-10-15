from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ExternalServiceProviderOption(BaseModel):
    code: str
    label: str
    fields: list[str] = Field(default_factory=list)
    docs_url: Optional[str] = None


class ExternalServicePublic(BaseModel):
    """Jamais la clé elle-même : seulement api_key_configured + 4 derniers
    caractères (key_last4)."""

    service: str
    label: str
    description: Optional[str] = None
    providers: list[ExternalServiceProviderOption]
    # Ligne configurée pour ce périmètre exact (projet, ou global si project_id absent)
    id: Optional[str] = None
    project_id: Optional[str] = None
    provider: Optional[str] = None
    api_key_configured: bool = False
    key_last4: Optional[str] = None
    config: dict = Field(default_factory=dict)
    last_test_status: Optional[str] = None
    last_test_error: Optional[str] = None
    last_tested_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Ce qui sera réellement utilisé : project | global | env | None
    effective_source: Optional[str] = None
    effective_provider: Optional[str] = None
    effective_key_last4: Optional[str] = None


class ExternalServiceUpsert(BaseModel):
    provider: str
    # Absent = conserver la clé déjà enregistrée (même provider uniquement)
    api_key: Optional[str] = None
    config: Optional[dict] = None


class ExternalServiceTestRequest(BaseModel):
    """Optionnel : tester une clé saisie avant de l'enregistrer."""

    provider: Optional[str] = None
    api_key: Optional[str] = None
    config: Optional[dict] = None


class ExternalServiceTestResult(BaseModel):
    service: str
    provider: Optional[str] = None
    source: Optional[str] = None
    status: str
    message: Optional[str] = None
