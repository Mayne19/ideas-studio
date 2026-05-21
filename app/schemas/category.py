from datetime import datetime
from typing import Optional
import re
from pydantic import BaseModel, ConfigDict, field_validator


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate_hex_color(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    if not HEX_COLOR_RE.match(normalized):
        raise ValueError("La couleur doit être un code hexadécimal valide, par exemple #2563eb.")
    return normalized.lower()


class CategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    priority: int = 0
    target_frequency: Optional[int] = None
    priority_score: Optional[float] = None
    monthly_frequency: Optional[int] = None
    pipeline_enabled: bool = True
    editorial_goal: Optional[str] = None
    target_audience: Optional[str] = None
    internal_notes: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return validate_hex_color(value)


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    priority: Optional[int] = None
    target_frequency: Optional[int] = None
    priority_score: Optional[float] = None
    monthly_frequency: Optional[int] = None
    pipeline_enabled: Optional[bool] = None
    editorial_goal: Optional[str] = None
    target_audience: Optional[str] = None
    internal_notes: Optional[str] = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return validate_hex_color(value)


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    slug: str
    description: Optional[str]
    color: Optional[str]
    priority: int
    target_frequency: Optional[int]
    priority_score: Optional[float] = None
    monthly_frequency: Optional[int] = None
    pipeline_enabled: Optional[bool] = None
    editorial_goal: Optional[str] = None
    target_audience: Optional[str] = None
    internal_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
