from pydantic import BaseModel


class EditorialSetupSuggestion(BaseModel):
    description: str
    audience: str
    tone: str
    positioning: str
    main_keywords: list[str]
    recommended_categories: list[str]
    seo_writing_guidelines: str


class EditorialSetupResponse(BaseModel):
    suggestion: EditorialSetupSuggestion
    source: str  # "llm" or "default"
    project_has_data: bool
