from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Ideas Studio"
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    DATABASE_URL: str = "sqlite:///./ideas_studio.db"
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    IDEAS_PER_DAY: int = 1
    DEFAULT_LLM_PROVIDER: str = "mock"
    DEFAULT_SEARCH_PROVIDER: str = "mock"
    OLLAMA_URL: str = ""
    OLLAMA_MODEL: str = "llama3.2"
    SEARXNG_URL: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
