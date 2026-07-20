import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "generate_a_secure_random_key_here"

    # Database Settings
    DATABASE_URL: str = "postgresql://scout_user:scout_secure_password@db:5432/scout_db"

    # Redis Settings
    REDIS_URL: str = "redis://redis:6379/0"

    # Celery Settings
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # Qdrant Settings
    QDRANT_URL: str = "http://qdrant:6333"

    # JWT Settings
    JWT_SECRET_KEY: str = "supersecretjwtkeyplaceholder"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # API Keys
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    DEEPSEEK_API_KEY: str | None = None

    # Monitoring & Logging
    LOG_LEVEL: str = "info"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
