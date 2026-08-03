from datetime import datetime
from typing import Literal, Optional
import re

from pydantic import BaseModel, field_validator


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

    @field_validator("color_background", "color_border", "color_text")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_hex(value)


class CalloutTemplateCreate(CalloutTemplateBase):
    label: str
    source: Literal["manual", "imported"] = "manual"
    external_id: Optional[str] = None
    settings_json: Optional[str] = None


class CalloutTemplateUpdate(CalloutTemplateBase):
    label: Optional[str] = None
    source: Optional[Literal["manual", "imported"]] = None
    external_id: Optional[str] = None


class CalloutTemplatePublic(BaseModel):
    id: str
    project_id: str
    slug: str
    label: str
    style: Optional[str] = None
    default_title: Optional[str] = None
    color_background: Optional[str] = None
    color_border: Optional[str] = None
    color_text: Optional[str] = None
    icon: Optional[str] = None
    source: str = "manual"
    external_id: Optional[str] = None
    class_name: Optional[str] = None
    created_at: datetime
