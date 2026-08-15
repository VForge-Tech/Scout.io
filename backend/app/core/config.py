from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings

from app.core.secrets import get_secret_manager, init_secret_manager


class Settings(BaseSettings):
    app_name: str = "Scout.io"
    debug: bool = False

    # These will be populated from Vault/env at runtime
    database_url: str = ""
    redis_url: str = ""
    qdrant_url: str = ""
    qdrant_api_key: str | None = None

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    together_api_key: str | None = None
    gemini_api_key: str | None = None
    azure_openai_api_key: str | None = None

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

    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # Razorpay billing (test-mode keys; provisioned via Vault in production)
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None

    # Billing feature flag. Disabled by default (testing/dev builds) so plan
    # limits are not enforced and checkout/webhook endpoints return 503.
    # Enable with BILLING_ENABLED=true in production.
    billing_enabled: bool = False

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    rate_limit_per_ip: str = "100/minute"
    rate_limit_per_org: str = "1000/minute"

    # Feature flags (default ON for backward compatibility)
    qdrant_enabled: bool = True
    litellm_enabled: bool = True
    celery_enabled: bool = True

    # Optional pgvector fallback
    pgvector_enabled: bool = False

    # Observability
    grafana_base_url: str = "http://grafana:3000"

    # Optional Ollama local LLM
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3.2"

    # Docker compose profile selection
    deployment_profile: str = "full"  # "full" or "minimal"

    model_config = {"env_file": ".env", "extra": "allow"}

    def __init__(self, **kwargs):
        # Initialize secret manager before calling parent init
        secret_manager = get_secret_manager()
        # Populate secret fields from Vault/env
        secrets = {
            "database_url": secret_manager.get_database_url(),
            "redis_url": secret_manager.get_redis_url(),
            "qdrant_url": secret_manager.get_qdrant_url(),
            "qdrant_api_key": secret_manager.get_qdrant_api_key(),
            "jwt_secret": secret_manager.get_jwt_secret(),
            "openai_api_key": secret_manager.get_openai_api_key(),
            "anthropic_api_key": secret_manager.get_anthropic_api_key(),
            "together_api_key": secret_manager.get_together_api_key(),
            "gemini_api_key": secret_manager.get_gemini_api_key(),
            "azure_openai_api_key": secret_manager.get_azure_openai_api_key(),
            "celery_broker_url": secret_manager.get_celery_broker_url(),
            "celery_result_backend": secret_manager.get_celery_result_backend(),
            "razorpay_key_id": secret_manager.get_razorpay_key_id(),
            "razorpay_key_secret": secret_manager.get_razorpay_key_secret(),
            "razorpay_webhook_secret": secret_manager.get_razorpay_webhook_secret(),
        }
        # Merge with any provided kwargs (kwargs takes precedence)
        merged = {**secrets, **kwargs}
        super().__init__(**merged)


@lru_cache
def get_settings() -> Settings:
    return Settings()
