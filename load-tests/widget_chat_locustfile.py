"""Multi-org widget chat load test.

Scenarios:
1. Baseline chat: every org sends a steady stream of widget messages.
2. Starvation check: a subset of orgs ("bursty") are driven much harder than the
   rest. The per-org rate limiter (rate_limit_per_org, default 1000/min) should
   cap the bursty orgs so normal orgs keep getting 2xx. The run report compares
   the bursty vs normal groups' 429 ratio and latency.

Per-stage latencies are harvested from the X-Pipeline-Timings header and fired
as separate Locust events (see common.fire_stage_events), so the web UI and CSV
report percentiles per stage (cache_lookup, retrieval, llm_generate, ...).

Run:
    cd load-tests
    locust -f widget_chat_locustfile.py
  # or headless with a ramp:
    locust -f widget_chat_locustfile.py --host http://localhost:8000 \
      --headless -u 200 -r 20 --run-time 10m --csv=reports/widget_chat
"""

from __future__ import annotations

import random

from locust import HttpUser, LoadTestShape, between, events, task

from common import (
    TIMINGS_HEADER,
    build_org_pools,
    fire_stage_events,
    load_seed_state,
    message_text,
    pick_org_session,
)

MESSAGE_PATH = "/api/v1/widget/messages"
# Requests per user per second (wait time floor) — tune with RATE env
RATE = 2.0


class WidgetChatUser(HttpUser):
    """Each simulated user is assigned to one org (bursty or normal)."""

    wait_time = between(1 / RATE, 3 / RATE)

    def on_start(self):
        seed = load_seed_state()
        self.bursty, self.normal = build_org_pools(seed)
        # User-level role: ~30% of users hammer a bursty org, rest normal.
        if random.random() < 0.3 and self.bursty:
            self.pool = "bursty"
            self.org = random.choice(self.bursty)
        else:
            self.pool = "normal"
            self.org = random.choice(self.normal or self.bursty)
        self.sess = pick_org_session(self.org)
        self.task_name = f"widget/{self.pool}"

    @task
    def send_message(self):
        sess = pick_org_session(self.org)
        payload = {"session_id": sess["session_id"], "content": message_text(random.randrange(8))}
        with self.client.post(
            MESSAGE_PATH,
            json=payload,
            headers={"Authorization": f"Bearer {sess['token']}"},
            name=self.task_name,
            catch_response=True,
        ) as resp:
            fire_stage_events(resp, self.task_name)
            if resp.status_code == 429:
                resp.failure("429 rate-limited")
            elif resp.status_code >= 500:
                resp.failure(f"5xx server error: {resp.status_code}")
            elif resp.status_code != 200:
                resp.failure(f"unexpected status {resp.status_code}")


# ---------------------------------------------------------------------------
# Ramp shape: baseline (1x) -> 10x concurrency, then hold. Enables the "burst"
# starvation run with a single command:
#   locust -f widget_chat_locustfile.py --headless --run-time 15m \
#     --users 20 --spawn-rate 5  (spawn-rate is scaled inside the shape)
# ---------------------------------------------------------------------------
class RampShape(LoadTestShape):
    """Linearly ramp users from `start_users` to `start_users * 10` over the
    first `ramp_seconds`, then hold at peak for `hold_seconds`."""

    start_users = 20
    ramp_seconds = 5 * 60
    hold_seconds = 5 * 60

    def tick(self):
        run_time = self.get_run_time()
        if run_time < self.ramp_seconds:
            frac = run_time / self.ramp_seconds
            user_count = int(self.start_users * (1 + 9 * frac))
            return (user_count, 10)
        if run_time < self.ramp_seconds + self.hold_seconds:
            return (self.start_users * 10, 10)
        return None
