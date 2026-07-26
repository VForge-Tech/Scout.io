import json

import redis

from app.core.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are Scout, an AI assistant that helps users understand their knowledge base. You provide accurate, helpful answers based on the retrieved context. If you don't know the answer, say so. Never make up information."""


class SessionMemory:
    def __init__(self, redis_client=None):
        self.client = redis_client or redis.from_url(settings.redis_url)
        self.ttl = settings.redis_session_ttl_seconds
        self.max_messages = 20

    def get_history(self, session_id: str) -> list[dict]:
        key = f"session:{session_id}:history"
        raw = self.client.lrange(key, -self.max_messages, -1)
        messages = []
        for item in raw:
            try:
                messages.append(json.loads(item))
            except (json.JSONDecodeError, TypeError):
                continue
        return messages

    def add_message(self, session_id: str, role: str, content: str):
        key = f"session:{session_id}:history"
        message = {"role": role, "content": content}
        self.client.rpush(key, json.dumps(message))
        self.client.ltrim(key, -self.max_messages, -1)
        self.client.expire(key, self.ttl)

    def build_context(
        self,
        session_id: str,
        retrieved_context: str = "",
    ) -> list[dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if retrieved_context:
            messages.append({
                "role": "system",
                "content": f"Here is relevant information from the knowledge base:\n\n{retrieved_context}",
            })

        history = self.get_history(session_id)
        messages.extend(history)

        return messages

    def clear_session(self, session_id: str):
        key = f"session:{session_id}:history"
        self.client.delete(key)
