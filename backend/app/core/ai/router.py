import logging

import litellm
from litellm import completion as litellm_completion

from app.core.ai.config import get_fallback_chain, get_model_config
from app.core.config import get_settings
from app.core.metrics import LLM_FALLBACK_TRIGGERS

logger = logging.getLogger(__name__)
settings = get_settings()


class AIRouter:
    def __init__(self, behaviour: str = "balanced"):
        self.behaviour = behaviour
        model_config = get_model_config(behaviour)
        self.primary_model = model_config.model
        self.max_tokens = model_config.max_tokens
        # Captured from the last successful completion: model actually used,
        # plus token counts (used by ResponsePipeline to record LLMUsage).
        self.last_usage: dict | None = None

    def generate(
        self,
        messages: list[dict],
        max_tokens: int | None = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> str:
        self.last_usage = None

        # Load-test mode: deterministic canned reply, no provider call.
        if settings.mock_llm:
            return self._mock_generate(messages, max_tokens)

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
                    content = self._handle_stream(response)
                    if content:
                        self.last_usage = self._capture_usage(model, messages, content, response)
                        return content
                content = response.choices[0].message.content
                if content:
                    self.last_usage = self._capture_usage(model, messages, content, response)
                    return content
            except Exception as e:
                logger.warning("Model %s failed: %s, trying fallback", model, e)
                LLM_FALLBACK_TRIGGERS.labels(
                    primary_model=self.primary_model, fallback_model=model
                ).inc()
                continue

        return self._graceful_error_response()

    def _mock_generate(self, messages: list[dict], max_tokens: int | None) -> str:
        """Deterministic canned reply for MOCK_LLM load-test mode.

        Mirrors the shapes the real provider returns (token usage captured on
        self.last_usage) so downstream billing/validation code paths still run.
        Adds a small fixed latency (~120ms) to keep the pipeline representative.
        """
        import time

        time.sleep(0.12)
        user_content = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )
        reply = f"[mock] Load-test reply for: {user_content[:120]}"
        prompt_text = "".join(m.get("content") or "" for m in messages)
        self.last_usage = {
            "model": self.primary_model,
            "prompt_tokens": self.count_tokens(prompt_text),
            "completion_tokens": self.count_tokens(reply),
            "total_tokens": self.count_tokens(prompt_text) + self.count_tokens(reply),
        }
        return reply

    def _capture_usage(
        self, model: str, messages: list[dict], content: str, response=None
    ) -> dict:
        """Build a usage dict, preferring the provider-reported token counts."""
        prompt_tokens = completion_tokens = total_tokens = None
        usage = getattr(response, "usage", None) if response is not None else None
        if usage is not None:
            prompt_tokens = getattr(usage, "prompt_tokens", None)
            completion_tokens = getattr(usage, "completion_tokens", None)
            total_tokens = getattr(usage, "total_tokens", None)
        if prompt_tokens is None or completion_tokens is None:
            prompt_text = "".join(m.get("content") or "" for m in messages)
            prompt_tokens = self.count_tokens(prompt_text)
            completion_tokens = self.count_tokens(content)
        if total_tokens is None:
            total_tokens = prompt_tokens + completion_tokens
        return {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

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
