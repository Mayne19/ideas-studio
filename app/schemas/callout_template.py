from datetime import datetime
from typing import Literal, Optional
import json
import re

from pydantic import BaseModel, ConfigDict, field_validator


HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _validate_hex(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if normalized == "":
        return None
    if not HEX_COLOR_RE.match(normalized):
        raise ValueError("La couleur doit être un code hexadécimal valide, par exemple #2563eb.")
    return normalized.lower()


def _validate_settings_json(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    json.loads(normalized)
    return normalized


class CalloutTemplateBase(BaseModel):
    slug: Optional[str] = None
    label: Optional[str] = None
    style: Optional[str] = None
    default_title: Optional[str] = None
    color_background: Optional[str] = None
    color_border: Optional[str] = None
    color_text: Optional[str] = None
    icon: Optional[str] = None
    class_name: Optional[str] = None
    settings_json: Optional[str] = None

    @field_validator("color_background", "color_border", "color_text")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_hex(value)

    @field_validator("settings_json")
    @classmethod
    def validate_settings_json(cls, value: Optional[str]) -> Optional[str]:
        return _validate_settings_json(value)


class CalloutTemplateCreate(CalloutTemplateBase):
    label: str
    source: Literal["manual", "imported"] = "manual"
    external_id: Optional[str] = None


class CalloutTemplateUpdate(CalloutTemplateBase):
    label: Optional[str] = None
    source: Optional[Literal["manual", "imported"]] = None
    external_id: Optional[str] = None


class CalloutTemplatePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    slug: str
    label: str
    style: Optional[str]
    default_title: Optional[str]
    color_background: Optional[str]
    color_border: Optional[str]
    color_text: Optional[str]
    icon: Optional[str]
    source: str
    external_id: Optional[str]
    class_name: Optional[str]
    settings_json: Optional[str]
    created_at: datetime
    updated_at: datetime

