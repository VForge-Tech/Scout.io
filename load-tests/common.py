"""Shared helpers for the Scout.io Locust load-test suite.

Responsibilities:
- Locating + loading the seed-state JSON produced by seed.py
- Parsing the X-Pipeline-Timings response header into per-stage dicts
- Firing Locust request events per pipeline stage so p50/p95/p99 are reported
  for each stage (not just the whole request)
- Building per-org session/token pools for the multi-org starvation scenario
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

from locust import events
from locust.exception import StopUser

# Timing header set by app/api/endpoints/widget_api.py (JSON object of stage -> ms)
TIMINGS_HEADER = "X-Pipeline-Timings"

LOAD_TESTS_DIR = Path(__file__).resolve().parent
SEED_FILE_ENV = "SCOUT_SEED_FILE"
DEFAULT_SEED_FILE = LOAD_TESTS_DIR / "seed_state.json"


def seed_path() -> Path:
    env = os.environ.get(SEED_FILE_ENV)
    return Path(env) if env else DEFAULT_SEED_FILE


def load_seed_state(path: Path | None = None) -> dict:
    p = path or seed_path()
    if not p.exists():
        raise StopUser(
            f"Seed state not found at {p}. Run `python load-tests/seed.py` first."
        )
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def pipeline_timings(response) -> dict[str, float]:
    """Parse X-Pipeline-Timings header; returns {} when absent."""
    raw = response.headers.get(TIMINGS_HEADER)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def fire_stage_events(response, request_name: str) -> None:
    """Emit one Locust request event per pipeline stage so percentile stats
    are collected per stage. Uses the request wall-clock response_time for the
    request itself and stage timings for each stage."""
    if response.request_meta is None:
        return
    meta = dict(response.request_meta)
    base_name = f"{request_name}[stage]"
    timings = pipeline_timings(response)
    if not timings:
        events.request.fire(**meta)  # already fired by Locust HTTPClient, ignore
        return
    for stage, ms in timings.items():
        stage_meta = dict(meta)
        stage_meta["name"] = f"{base_name}:{stage}"
        # fire with the stage's own latency; total stays on the request meta
        stage_meta["response_time"] = float(ms)
        events.request.fire(
            request_type=stage_meta.get("request_type", "POST"),
            name=stage_meta["name"],
            response_time=stage_meta["response_time"],
            response_length=0,
            response=stage_meta.get("response"),
            context=stage_meta.get("context"),
            exception=stage_meta.get("exception"),
        )


def build_org_pools(seed: dict, bursty_fraction: float = 0.2) -> tuple[list[dict], list[dict]]:
    """Split seeded orgs into bursty (high-touch) and normal (baseline) pools.

    Returns (bursty_orgs, normal_orgs). Each org dict contains:
    {"org_id", "chatbot_id", "sessions": [{"session_id", "token"}, ...]}
    """
    orgs = seed.get("orgs", [])
    if not orgs:
        raise StopUser("Seed state contains no orgs. Re-run seed.py.")
    random.shuffle(orgs)
    split = max(1, int(len(orgs) * bursty_fraction))
    return orgs[:split], orgs[split:]


def pick_org_session(org: dict) -> dict:
    """Pick a random session (with its widget token) from an org."""
    sessions = org.get("sessions", [])
    if not sessions:
        raise StopUser(f"Org {org['org_id']} has no widget sessions. Re-run seed.py.")
    return random.choice(sessions)


def message_text(index: int) -> str:
    """Deterministic, realistic user message to keep requests varied but reproducible."""
    templates = [
        "How do I reset my password?",
        "What are your pricing tiers?",
        "Tell me about the free plan limits.",
        "How do I invite a teammate?",
        "Where can I find the API docs?",
        "Can you cancel my subscription?",
        "How long do refunds take?",
        "What integrations do you support?",
    ]
    return templates[index % len(templates)]