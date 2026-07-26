from dataclasses import dataclass, field

from app.core.config import get_settings

settings = get_settings()


@dataclass
class ModelConfig:
    model: str
    provider: str
    max_tokens: int
    description: str
    cost_tier: str  # cheap, medium, expensive


DEFAULT_MODEL_MAP: dict[str, list[ModelConfig]] = {
    "fast": [
        ModelConfig(
            model=settings.fast_llm_model,
            provider="openai",
            max_tokens=settings.max_response_tokens,
            description="Quick responses for simple queries",
            cost_tier="cheap",
        ),
    ],
    "balanced": [
        ModelConfig(
            model=settings.balanced_llm_model,
            provider="openai",
            max_tokens=settings.max_response_tokens,
            description="General purpose responses",
            cost_tier="medium",
        ),
    ],
    "accurate": [
        ModelConfig(
            model=settings.accurate_llm_model,
            provider="openai",
            max_tokens=settings.max_response_tokens,
            description="High quality responses for complex queries",
            cost_tier="expensive",
        ),
    ],
}

FALLBACK_CHAIN: list[str] = settings.fallback_models


def get_model_config(behaviour: str) -> ModelConfig:
    configs = DEFAULT_MODEL_MAP.get(behaviour, DEFAULT_MODEL_MAP["balanced"])
    return configs[0]


def get_fallback_chain(primary_model: str) -> list[str]:
    return [primary_model] + FALLBACK_CHAIN
