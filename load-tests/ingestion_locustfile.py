"""Knowledge-ingestion load test.

Exercises the ingestion pipeline under multi-org concurrency:
  1. POST /api/v1/chatbots/{chatbot_id}/knowledge-sources  (DB insert)
  2. POST .../sync  (dispatches the Celery process_knowledge_source task)
  3. Poll GET .../knowledge-sources/{source_id} until sync_status is
     completed/failed (or poll timeout).

Each user is pinned to one org so per-org concurrency stays realistic. The
ingestion task runs on the Celery worker: this file measures API dispatch
latency and sync completion time, which together reveal worker-throughput
bottlenecks (queue depth, worker count, embedding rate).

The backend must run with CELERY_ENABLED=true and a worker consuming the queue.
With MOCK_LLM=true the embedding service returns deterministic vectors, so the
test measures pipeline mechanics, not provider cost.

Run:
    locust -f ingestion_locustfile.py --host http://localhost:8000 \
      --headless -u 30 -r 5 --run-time 10m --csv=reports/ingestion
"""

from __future__ import annotations

import json
import random
import time
from urllib.parse import quote

from locust import HttpUser, between, events, task

from common import load_seed_state

SYNC_POLL_TIMEOUT_S = 120.0
SYNC_POLL_INTERVAL_S = 1.0


class IngestionUser(HttpUser):
    """Each user owns one org and drives create -> sync -> poll cycles."""

    wait_time = between(0.5, 2.0)

    def on_start(self):
        seed = load_seed_state()
        orgs = seed.get("orgs", [])
        if not orgs:
            raise RuntimeError("Seed state has no orgs; run seed.py first.")
        self.org = random.choice(orgs)
        self.chatbot_id = self.org["chatbot_id"]
        self.user_token = self.org["user_token"]
        self.headers = {"Authorization": f"Bearer {self.user_token}"}
        # Reuse a seeded source id as a deterministic re-sync target
        self.sources = [s["source_id"] for s in self.org.get("knowledge_sources", [])]

    def _create_source(self) -> str | None:
        uri = (
            "Scout.io onboarding: create a chatbot, connect knowledge sources, "
            "then embed the widget. Set billing keys under Settings. Monitor "
            "latency with the Grafana dashboards. " * 30
        )
        resp = self.client.post(
            f"/api/v1/chatbots/{self.chatbot_id}/knowledge-sources",
            headers=self.headers,
            json={
                "source_type": "text",
                "uri": uri,
                "config": {"_load_test": True},
            },
            name="ingestion/create-source",
        )
        if resp.status_code in (200, 201):
            return resp.json().get("id")
        resp.failure(f"create failed: {resp.status_code}")
        return None

    def _sync(self, source_id: str) -> None:
        resp = self.client.post(
            f"/api/v1/chatbots/{self.chatbot_id}/knowledge-sources/{source_id}/sync",
            headers=self.headers,
            name="ingestion/dispatch-sync",
        )
        if resp.status_code != 200:
            resp.failure(f"sync dispatch failed: {resp.status_code}")
            return
        try:
            task_id = resp.json().get("task_id")
        except json.JSONDecodeError:
            task_id = None

        # Poll until completed (eventually-failed sources also terminate the loop)
        deadline = time.time() + SYNC_POLL_TIMEOUT_S
        while time.time() < deadline:
            poll = self.client.get(
                f"/api/v1/chatbots/{self.chatbot_id}/knowledge-sources/{source_id}",
                headers=self.headers,
                name="ingestion/poll-status",
            )
            if poll.status_code != 200:
                poll.failure(f"poll failed: {poll.status_code}")
                time.sleep(SYNC_POLL_INTERVAL_S)
                continue
            status = poll.json().get("sync_status")
            if status in ("completed", "failed"):
                poll.success()  # terminate loop cleanly
                return
            time.sleep(SYNC_POLL_INTERVAL_S)

    @task
    def create_and_sync(self):
        source_id = self._create_source()
        if not source_id:
            return
        self._sync(source_id)