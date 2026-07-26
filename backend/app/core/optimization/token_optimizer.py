from app.core.config import get_settings
from app.core.ai.router import AIRouter

settings = get_settings()


class TokenOptimizer:
    def __init__(self, ai_router: AIRouter | None = None):
        self.router = ai_router or AIRouter(behaviour="fast")
        self.max_context_tokens = settings.max_context_tokens

    def compress_context(self, context: str, query: str) -> str:
        if not context:
            return ""

        token_count = self.router.count_tokens(context)
        if token_count <= self.max_context_tokens:
            return context

        chunks = context.split("\n\n[Source ")
        compressed = []
        current_tokens = 0

        for chunk in chunks:
            if not chunk.strip():
                continue
            chunk_text = f"[Source {chunk}" if not chunk.startswith("[Source") else chunk
            chunk_tokens = self.router.count_tokens(chunk_text)
            if current_tokens + chunk_tokens <= self.max_context_tokens:
                compressed.append(chunk_text)
                current_tokens += chunk_tokens
            else:
                remaining = self.max_context_tokens - current_tokens
                if remaining > 50:
                    words = chunk_text.split()
                    truncated = " ".join(words[:len(words) * remaining // chunk_tokens])
                    compressed.append(truncated + "...")
                break

        return "\n\n".join(compressed)
