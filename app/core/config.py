from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Ideas Studio"
    APP_ENV: str = "development"
    APP_URL: str = "http://localhost:8000"
    DATABASE_URL: str = "sqlite:///./ideas_studio.db"
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    model_config = {"env_file": ".env"}


settings = Settings()
