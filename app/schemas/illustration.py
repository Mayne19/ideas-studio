from typing import Optional

from pydantic import BaseModel, Field


class IllustrationOption(BaseModel):
    code: str
    label: str
    approx_cost_usd: Optional[float] = None


class IllustrationConfigPayload(BaseModel):
    model: Optional[str] = None
    style_preset: Optional[str] = None
    custom_style: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    max_images: Optional[int] = None


class IllustrationSettingsPublic(BaseModel):
    project_id: Optional[str] = None
    # Ligne enregistrée pour ce périmètre exact (sinon valeurs héritées)
    configured: bool = False
    # project | global | default
    effective_source: str = "default"
    mode: str
    config: dict = Field(default_factory=dict)
    modes: list[IllustrationOption]
    models: list[IllustrationOption]
    style_presets: list[IllustrationOption]
    max_images_limit: int
    # Clé OpenRouter disponible (Paramètres → Providers IA ou env)
    openrouter_configured: bool = False


class IllustrationSettingsUpsert(BaseModel):
    mode: str
    config: IllustrationConfigPayload = Field(default_factory=IllustrationConfigPayload)


class IllustrationPreviewRequest(BaseModel):
    """Réglages (non enregistrés) à tester ; sujet libre optionnel."""

    config: IllustrationConfigPayload = Field(default_factory=IllustrationConfigPayload)
    subject: Optional[str] = Field(default=None, max_length=300)


class IllustrationPreviewResult(BaseModel):
    image_data_url: str
    prompt: str
    model: str
    cost_usd: Optional[float] = None
