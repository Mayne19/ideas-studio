from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Ideas Studio"
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    DATABASE_URL: str = "sqlite:///./ideas_studio.db"
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    IDEAS_PER_DAY: int = 1
    MIN_GENERATED_ARTICLE_WORDS: int = 800
    WORDS_PER_READING_MINUTE: int = 220
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_SEARCH_PROVIDER: str = "mock"
    OLLAMA_URL: str = ""
    OLLAMA_MODEL: str = "llama3.2"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    SEARXNG_URL: str = ""

    UPLOAD_DIR: str = "uploads"

    BLOG_REVALIDATE_URL: str = ""
    BLOG_REVALIDATE_SECRET: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
