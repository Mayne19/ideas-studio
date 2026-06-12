import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Ideas Studio"
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    DATABASE_URL: str = "sqlite:///./ideas_studio.db"
    SECRET_KEY: str = secrets.token_urlsafe(48)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    IDEAS_PER_DAY: int = 1
    MIN_GENERATED_ARTICLE_WORDS: int = 800
    WORDS_PER_READING_MINUTE: int = 220
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
    CACHE_TTL_SECONDS: int = 3600
    DEFAULT_SEARCH_PROVIDER_UNSPLASH: str = "unsplash"

    PIPELINE_MODE: str = "ideas_only"
    PIPELINE_MAX_DAILY_IDEAS: int = 10
    PIPELINE_PUBLISH_IMMEDIATELY: bool = False

    AGENT_KEYWORD_RESEARCHER_PROVIDER: str = ""
    AGENT_KEYWORD_RESEARCHER_MODEL: str = ""
    AGENT_CONTENT_WRITER_PROVIDER: str = ""
    AGENT_CONTENT_WRITER_MODEL: str = ""
    AGENT_FACT_CHECKER_PROVIDER: str = ""
    AGENT_FACT_CHECKER_MODEL: str = ""
    AGENT_EDITOR_REVISOR_PROVIDER: str = ""
    AGENT_EDITOR_REVISOR_MODEL: str = ""
    AGENT_SEO_OPTIMIZER_PROVIDER: str = ""
    AGENT_SEO_OPTIMIZER_MODEL: str = ""
    AGENT_QUALITY_RATER_PROVIDER: str = ""
    AGENT_QUALITY_RATER_MODEL: str = ""

    UPLOAD_DIR: str = "uploads"

    BLOG_REVALIDATE_URL: str = ""
    BLOG_REVALIDATE_SECRET: str = ""

    AI_ROUTING_ENABLED: bool = True
    AI_FALLBACK_ENABLED: bool = True
    SEARCH_MAX_RESULTS: int = 8
    SCRAPER_PROVIDER: str = "basic"
    SCRAPER_MAX_PAGES: int = 5
    SCRAPER_TIMEOUT_SECONDS: int = 20
    SCRAPER_USER_AGENT: str = "IdeasStudioBot/1.0"
    GOOGLE_SEARCH_CONSOLE_ENABLED: bool = False
    GOOGLE_SEARCH_CONSOLE_SITE_URL: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    MISTRAL_API_KEY: str = ""
    MISTRAL_MODEL: str = "mistral-small-latest"
    GEMINI_WRITER_MODEL: str = ""
    GEMINI_EDITOR_MODEL: str = ""
    GEMINI_SEO_MODEL: str = ""
    GEMINI_RESEARCH_MODEL: str = ""
    GEMINI_META_MODEL: str = ""
    GEMINI_GROUNDING_ENABLED: bool = False
    GEMINI_GROUNDING_MAX_REQUESTS_PER_DAY: int = 500

    AGENT_PLANNER_PROVIDER: str = ""
    AGENT_PLANNER_MODEL: str = ""
    AGENT_RESEARCHER_PROVIDER: str = ""
    AGENT_RESEARCHER_MODEL: str = ""
    AGENT_WRITER_PROVIDER: str = ""
    AGENT_WRITER_MODEL: str = ""
    AGENT_EDITOR_PROVIDER: str = ""
    AGENT_EDITOR_MODEL: str = ""
    AGENT_SEO_PROVIDER: str = ""
    AGENT_SEO_MODEL: str = ""
    AGENT_FACT_CHECKER_PROVIDER: str = ""
    AGENT_FACT_CHECKER_MODEL: str = ""
    AGENT_META_PROVIDER: str = ""
    AGENT_META_MODEL: str = ""
    AGENT_PRODUCT_WRITER_PROVIDER: str = ""
    AGENT_PRODUCT_WRITER_MODEL: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
