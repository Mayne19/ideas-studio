import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.models.ai_provider_config import AIProviderConfig
from app.schemas.ai_provider import AIProviderCreate, AIProviderUpdate, AIProviderPublic, AIProviderTestResult
from app.services.providers.llm_provider import get_llm_provider
from app.core.config import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/ai-providers", tags=["ai_providers"])

SUPPORTED_PROVIDERS = {
    "gemini": {"label": "Google Gemini", "default_model": "gemini-2.5-flash", "default_base_url": "https://generativelanguage.googleapis.com/v1beta/openai/"},
    "openai": {"label": "OpenAI", "default_model": "gpt-4o-mini", "default_base_url": "https://api.openai.com/v1"},
    "openrouter": {"label": "OpenRouter", "default_model": "deepseek/deepseek-v4-flash:free", "default_base_url": "https://openrouter.ai/api/v1"},
    "anthropic": {"label": "Anthropic", "default_model": "claude-3-haiku-20240307", "default_base_url": "https://api.anthropic.com/v1"},
    "mistral": {"label": "Mistral AI", "default_model": "mistral-small-latest", "default_base_url": "https://api.mistral.ai/v1"},
    "ollama": {"label": "Ollama (local)", "default_model": "qwen3:14b", "default_base_url": "http://127.0.0.1:11434/v1"},
    "custom": {"label": "Custom OpenAI-compatible", "default_model": "", "default_base_url": ""},
}


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


@router.get("", response_model=list[AIProviderPublic])
def list_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    configs = db.query(AIProviderConfig).order_by(AIProviderConfig.provider).all()
    result = []
    for config in configs:
        public = AIProviderPublic.model_validate(config)
        public.api_key_configured = bool(config.api_key_encrypted)
        result.append(public)
    return result


@router.post("", response_model=AIProviderPublic, status_code=201)
def create_provider(
    data: AIProviderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    existing = db.query(AIProviderConfig).filter(AIProviderConfig.provider == data.provider).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Provider '{data.provider}' already configured")
    
    config = AIProviderConfig(
        provider=data.provider,
        label=data.label,
        api_key_encrypted=data.api_key,
        model=data.model,
        base_url=data.base_url,
        is_default=data.is_default,
        enabled=data.enabled,
    )
    
    if data.is_default:
        db.query(AIProviderConfig).filter(AIProviderConfig.is_default == True).update({"is_default": False})
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    public = AIProviderPublic.model_validate(config)
    public.api_key_configured = bool(config.api_key_encrypted)
    return public


@router.get("/{provider_id}", response_model=AIProviderPublic)
def get_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    config = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    public = AIProviderPublic.model_validate(config)
    public.api_key_configured = bool(config.api_key_encrypted)
    return public


@router.patch("/{provider_id}", response_model=AIProviderPublic)
def update_provider(
    provider_id: str,
    data: AIProviderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    config = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    update_data = data.model_dump(exclude_unset=True)
    if "api_key" in update_data:
        update_data["api_key_encrypted"] = update_data.pop("api_key")
    if "is_default" in update_data and update_data["is_default"]:
        db.query(AIProviderConfig).filter(AIProviderConfig.is_default == True, AIProviderConfig.id != provider_id).update({"is_default": False})
    
    for field, value in update_data.items():
        setattr(config, field, value)
    
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    
    public = AIProviderPublic.model_validate(config)
    public.api_key_configured = bool(config.api_key_encrypted)
    return public


@router.delete("/{provider_id}", status_code=204)
def delete_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    config = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    db.delete(config)
    db.commit()
    return None


@router.post("/{provider_id}/test", response_model=AIProviderTestResult)
def test_provider(
    provider_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_platform_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    config = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Provider not found")
    
    if not config.api_key_encrypted:
        config.last_test_status = "error"
        config.last_test_error = "Aucune clé API configurée"
        config.last_tested_at = datetime.now(timezone.utc)
        db.commit()
        return AIProviderTestResult(provider=config.provider, status="error", message="Aucune clé API configurée")
    
    try:
        from app.services.providers.openai_provider import OpenAILLMProvider
        
        test_prov = OpenAILLMProvider(
            api_key=config.api_key_encrypted,
            model=config.model or "gpt-4o-mini",
            base_url=config.base_url or "https://api.openai.com/v1",
            timeout_seconds=30,
        )
        available = test_prov.is_available()
        
        config.last_test_status = "connected" if available else "error"
        config.last_test_error = None if available else "API a retourné une erreur (clé invalide ?)"
        config.last_tested_at = datetime.now(timezone.utc)
        db.commit()
        
        return AIProviderTestResult(
            provider=config.provider,
            status="connected" if available else "error",
            message=None if available else config.last_test_error,
            model=config.model,
        )
    except Exception as exc:
        config.last_test_status = "error"
        config.last_test_error = str(exc)
        config.last_tested_at = datetime.now(timezone.utc)
        db.commit()
        return AIProviderTestResult(provider=config.provider, status="error", message=str(exc))


@router.get("/default")
def get_default_provider(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = db.query(AIProviderConfig).filter(
        AIProviderConfig.is_default == True,
        AIProviderConfig.enabled == True,
    ).first()
    if config:
        return {
            "provider": config.provider,
            "model": config.model,
            "configured": bool(config.api_key_encrypted),
            "enabled": config.enabled,
        }
    # Fall back to env settings
    return {
        "provider": settings.DEFAULT_LLM_PROVIDER,
        "model": getattr(settings, f"{settings.DEFAULT_LLM_PROVIDER.upper()}_MODEL", None),
        "configured": False,
        "enabled": True,
        "source": "env",
    }
