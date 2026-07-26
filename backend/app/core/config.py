from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Scout.io"
    debug: bool = False

    database_url: str = "postgresql://scout:changeme@localhost:5432/scout"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    jwt_secret: str = "change-me-to-a-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    together_api_key: str | None = None
    gemini_api_key: str | None = None

    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    qdrant_collection: str = "scout_knowledge"

    fast_llm_model: str = "gpt-3.5-turbo"
    balanced_llm_model: str = "gpt-4o-mini"
    accurate_llm_model: str = "gpt-4o"
    fallback_models: list[str] = ["claude-3-haiku-20240307", "gemini/gemini-1.5-flash"]

    max_context_tokens: int = 4096
    max_response_tokens: int = 1024
    top_k_retrieval: int = 5

    redis_session_ttl_seconds: int = 3600
    redis_knowledge_cache_ttl: int = 300
    redis_optimization_cache_ttl: int = 600

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    rate_limit_per_ip: str = "100/minute"
    rate_limit_per_org: str = "1000/minute"

    # Feature flags (default ON for backward compatibility)
    qdrant_enabled: bool = True
    litellm_enabled: bool = True
    celery_enabled: bool = True

    # Optional pgvector fallback
    pgvector_enabled: bool = False

    # Optional Ollama local LLM
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3.2"

    # Docker compose profile selection
    deployment_profile: str = "full"  # "full" or "minimal"

    model_config = {"env_file": ".env", "extra": "allow"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
