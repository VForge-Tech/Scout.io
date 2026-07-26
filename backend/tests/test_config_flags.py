from app.core.config import get_settings


def test_default_feature_flags():
    settings = get_settings()
    assert settings.qdrant_enabled is True
    assert settings.litellm_enabled is True
    assert settings.celery_enabled is True
    assert settings.pgvector_enabled is False
    assert settings.ollama_enabled is False
    assert settings.deployment_profile == "full"
