import logging

import litellm
from litellm import completion as litellm_completion

from app.core.ai.config import get_fallback_chain, get_model_config
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AIRouter:
    def __init__(self, behaviour: str = "balanced"):
        self.behaviour = behaviour
        model_config = get_model_config(behaviour)
        self.primary_model = model_config.model
        self.max_tokens = model_config.max_tokens

    def generate(
        self,
        messages: list[dict],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str:
        fallback_models = get_fallback_chain(self.primary_model)

        for model in fallback_models:
            try:
                response = litellm_completion(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens or self.max_tokens,
                    temperature=temperature,
                    stream=stream,
                )
                if stream:
                    return self._handle_stream(response)
                content = response.choices[0].message.content
                if content:
                    return content
            except Exception as e:
                logger.warning("Model %s failed: %s, trying fallback", model, e)
                continue

        return self._graceful_error_response()

    def _handle_stream(self, response) -> str:
        full_content = ""
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            full_content += delta
        return full_content

    def _graceful_error_response(self) -> str:
        return "I'm sorry, I'm having trouble processing your request right now. Please try again later."

    def count_tokens(self, text: str) -> int:
        try:
            return litellm.token_counter(model=self.primary_model, text=text)
        except Exception:
            return len(text) // 2  # rough estimate


def get_ai_router(behaviour: str = "balanced") -> AIRouter:
    return AIRouter(behaviour=behaviour)
