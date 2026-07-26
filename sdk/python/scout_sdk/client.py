from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScoutConfig:
    api_key: str
    base_url: str = "https://api.scout.io"
    timeout: int = 30


class ScoutClient:
    def __init__(self, config: ScoutConfig):
        self.config = config
        self._session: Any | None = None

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        import httpx

        url = f"{self.config.base_url}{path}"
        resp = httpx.request(
            method=method,
            url=url,
            headers=self._headers,
            timeout=self.config.timeout,
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json()

    def send_message(self, chatbot_id: str, content: str, session_id: str | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/widget/chatbots/{chatbot_id}/messages",
            json={"content": content, "session_id": session_id},
        )

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/widget/sessions/{session_id}/messages")

    def search_knowledge(self, organization_id: str, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self._request(
            "POST",
            "/api/v1/retrieval/search",
            json={"organization_id": organization_id, "query": query, "top_k": top_k},
        )
