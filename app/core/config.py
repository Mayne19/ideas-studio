import logging
import os
import secrets

from pydantic import field_validator
from pydantic_settings import BaseSettings
from sqlalchemy.engine.url import make_url


class Settings(BaseSettings):
    APP_NAME: str = "Ideas Studio"
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = ""
    CORS_ORIGINS: str = ""
    DATABASE_URL: str = "sqlite:///./ideas_studio.db"
    SECRET_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    IDEAS_PER_DAY: int = 1
    DEFAULT_LLM_PROVIDER: str = "auto"
    DEFAULT_SEARCH_PROVIDER: str = "mock"
    OLLAMA_URL: str = ""
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3:14b"
    OLLAMA_FALLBACK_MODEL: str = "qwen3:8b"
    OLLAMA_TIMEOUT_SECONDS: int = 180
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "deepseek/deepseek-v4-flash:free"
    OPENROUTER_WRITER_MODEL: str = "deepseek/deepseek-v4-flash:free"
    OPENROUTER_PLANNER_MODEL: str = "openai/gpt-oss-120b:free"
    OPENROUTER_FALLBACK_MODEL: str = "openrouter/free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_TIMEOUT_SECONDS: int = 180
    SEARXNG_URL: str = ""
    SERP_API_KEY: str = ""
    UNSPLASH_ACCESS_KEY: str = ""
    SEARXNG_FORMAT: str = "json"
    SEARCH_TIMEOUT_SECONDS: int = 30
    GOOGLE_SEARCH_API_KEY: str = ""
    GOOGLE_SEARCH_CX: str = ""
    BRAVE_SEARCH_API_KEY: str = ""

    PIPELINE_MODE: str = "ideas_only"

    UPLOAD_DIR: str = "uploads"

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "ideas-media"

    BLOG_REVALIDATE_URL: str = ""
    BLOG_REVALIDATE_SECRET: str = ""

    GA4_PROPERTY_ID: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str, info) -> str:
        if not v:
            app_env = info.data.get("APP_ENV") or os.getenv("APP_ENV", "development")
            if app_env == "production":
                raise ValueError(
                    "SECRET_KEY must be explicitly set in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
            # En développement uniquement : générer une clé temporaire avec avertissement
            logging.getLogger(__name__).warning(
                "SECRET_KEY not set — using temporary random key (dev only). "
                "All sessions and encrypted API keys will be lost on restart."
            )
            return secrets.token_urlsafe(48)
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_be_postgres(cls, v: str, info) -> str:
        # Schéma v3 (schémas nommés, RLS, jsonb, ENUM natifs, partitionnement) : n'a de
        # sens que sur PostgreSQL. SQLite silencieusement toléré est justement ce qui a
        # permis à l'app de tourner (et de sembler fonctionner) contre un schéma que le
        # code ne décrit plus — voir REPRENDRE-LA-MAIN.md §1.
        # Exception "test" : tests/conftest.py utilise encore SQLite en attendant sa
        # propre migration vers Postgres (non encore faite à ce stade de la refonte).
        app_env = info.data.get("APP_ENV") or os.getenv("APP_ENV", "development")
        if app_env == "test":
            return v
        normalized = v.replace("postgres://", "postgresql://", 1)
        if not normalized.startswith("postgresql"):
            raise ValueError(
                f"DATABASE_URL doit pointer vers PostgreSQL (schéma v3 : RLS, jsonb, "
                f"ENUM natifs, partitionnement). Reçu : {normalized.split('://')[0]}://..."
            )
        return v

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql://", 1)
        return self.DATABASE_URL

    @property
    def safe_database_url(self) -> str:
        try:
            return make_url(self.database_url).render_as_string(hide_password=True)
        except Exception:
            return "<invalid database url>"

    @property
    def cors_origins_list(self) -> list[str]:
        configured = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if self.FRONTEND_URL and self.FRONTEND_URL not in configured:
            configured.append(self.FRONTEND_URL)
        if self.APP_ENV == "development":
            for port in range(5173, 5180):
                for host in ("http://localhost", "http://127.0.0.1"):
                    origin = f"{host}:{port}"
                    if origin not in configured:
                        configured.append(origin)
        if not configured and self.APP_ENV == "production":
            raise ValueError(
                "CORS_ORIGINS must be set in production. "
                "Set CORS_ORIGINS or FRONTEND_URL environment variable."
            )
        return configured or ["*"]


settings = Settings()
