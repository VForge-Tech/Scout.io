"""Prometheus instrumentation for Scout.io.

Exposes:
- HTTP request rate / latency / error count per endpoint (middleware)
- Celery task success / failure counts + queue depth (signals + Redis sampler)
- Dependency health gauges reusing ``app.core.health.check_dependencies``
- LLM provider fallback trigger count

The ``/metrics`` endpoint is registered on the FastAPI app by ``setup_metrics``.
"""

import logging
import threading
import time
import uuid
from typing import Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

HTTP_REQUESTS = Counter(
    "scout_http_requests_total",
    "Total HTTP requests handled, by method / route template / status code",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "scout_http_request_duration_seconds",
    "HTTP request latency in seconds, by method and route template",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

CELERY_TASKS = Counter(
    "scout_celery_tasks_total",
    "Celery tasks by task name and outcome (success/failure)",
    ["task", "state"],
)

CELERY_QUEUE_DEPTH = Gauge(
    "scout_celery_queue_depth",
    "Current number of messages pending in the Celery broker queue",
    ["queue"],
)

DEPENDENCY_HEALTH = Gauge(
    "scout_dependency_health",
    "1 if the dependency is healthy, 0 otherwise. Labels match /health/ready services",
    ["service"],
)

LLM_FALLBACK_TRIGGERS = Counter(
    "scout_llm_fallback_triggers_total",
    "Number of times a model call failed and the router fell back to the next model",
    ["primary_model", "fallback_model"],
)

# ---------------------------------------------------------------------------
# Celery signals (task success / failure)
# ---------------------------------------------------------------------------

_celery_signals_registered = False


def _on_celery_task_success(sender=None, task_id=None, **kwargs):
    name = getattr(sender, "name", "unknown")
    CELERY_TASKS.labels(task=name, state="success").inc()


def _on_celery_task_failure(sender=None, task_id=None, **kwargs):
    name = getattr(sender, "name", "unknown")
    CELERY_TASKS.labels(task=name, state="failure").inc()


def register_celery_metrics() -> None:
    """Connect Celery signal handlers once (idempotent)."""
    global _celery_signals_registered
    if _celery_signals_registered:
        return
    from celery import signals

    signals.task_success.connect(_on_celery_task_success)
    signals.task_failure.connect(_on_celery_task_failure)
    _celery_signals_registered = True
    logger.debug("Celery metrics signals registered")


# ---------------------------------------------------------------------------
# Background sampler: queue depth + dependency health
# ---------------------------------------------------------------------------

QUEUES = ("celery",)


def _sample_queue_depths() -> None:
    settings = get_settings()
    try:
        import redis

        r = redis.from_url(settings.celery_broker_url or settings.redis_url, socket_connect_timeout=2)
        for queue in QUEUES:
            try:
                CELERY_QUEUE_DEPTH.labels(queue=queue).set(int(r.llen(queue)))
            except Exception:  # noqa: BLE001
                CELERY_QUEUE_DEPTH.labels(queue=queue).set(-1)
        r.close()
    except Exception as e:  # noqa: BLE001
        logger.debug("Queue depth sampler failed: %s", e)


def _sample_dependency_health() -> None:
    from app.core.health import check_dependencies

    services = check_dependencies()
    for service, status in services.items():
        DEPENDENCY_HEALTH.labels(service=service).set(1 if status == "ok" else 0)


class _MetricsSampler(threading.Thread):
    """Periodically refresh gauges that can't be pushed synchronously."""

    def __init__(self, interval: float = 15.0):
        super().__init__(daemon=True, name="metrics-sampler")
        self.interval = interval
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                _sample_queue_depths()
            except Exception as e:  # noqa: BLE001
                logger.debug("Queue depth sampling error: %s", e)
            try:
                _sample_dependency_health()
            except Exception as e:  # noqa: BLE001
                logger.debug("Dependency health sampling error: %s", e)

    def stop(self) -> None:
        self._stop.set()


# ---------------------------------------------------------------------------
# HTTP request metrics middleware
# ---------------------------------------------------------------------------

_SKIPPED_PATHS = {"/metrics", "/health", "/health/ready"}


def _route_template(request: Request) -> str:
    """Resolve the matched route path template for low-cardinality labels."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if path:
        return path
    # Fall back to the first two path segments to bound cardinality for 404s.
    segments = request.url.path.strip("/").split("/")
    return "/" + "/".join(segments[:2]) if segments[0] else "/"


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIPPED_PATHS:
            return await call_next(request)

        path = _route_template(request)
        method = request.method
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            HTTP_REQUESTS.labels(method=method, path=path, status="500").inc()
            HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(
                time.perf_counter() - start
            )
            raise
        HTTP_REQUESTS.labels(method=method, path=path, status=str(response.status_code)).inc()
        HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(
            time.perf_counter() - start
        )
        self._log_request(request, method, path, response.status_code, start)
        return response

    @staticmethod
    def _log_request(request, method: str, path: str, status_code: int, start: float) -> None:
        trace_id = getattr(request.state, "trace_id", None) or str(uuid.uuid4())
        request_logger = logging.getLogger("scout.request")
        request_logger.info(
            "request_completed",
            extra={
                "trace_id": trace_id,
                "method": method,
                "path": path,
                "status": status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "grafana_link": grafana_log_link(trace_id),
            },
        )


# ---------------------------------------------------------------------------
# App wiring
# ---------------------------------------------------------------------------

_sampler: Optional[_MetricsSampler] = None


def setup_metrics(app) -> None:
    """Add the /metrics route, middleware, and start the background sampler."""
    from fastapi import FastAPI
    from fastapi.responses import Response as FastAPIResponse

    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        return FastAPIResponse(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    app.add_middleware(MetricsMiddleware)
    register_celery_metrics()

    global _sampler
    if _sampler is None:
        _sampler = _MetricsSampler()
        _sampler.start()


def trace_id_for_request(request: Request) -> str:
    """Return the request trace_id (set by TracingMiddleware)."""
    return getattr(request.state, "trace_id", None) or str(uuid.uuid4())


def grafana_log_link(trace_id: str, base_url: str = None) -> str:
    """Build a Grafana Explore (Loki) deep-link for a given trace_id.

    The link pattern lets an on-call engineer jump from an alert straight to the
    JSON logs carrying that trace_id. Override the base URL via
    GRAFANA_BASE_URL (default http://grafana:3000).
    """
    from urllib.parse import quote

    base = base_url or get_settings().grafana_base_url or "http://grafana:3000"
    query = quote(f'{{job="scout-backend"}} |= "trace_id": "{trace_id}"')
    return f"{base}/explore?orgId=1&left=now-6h&right=now&query={query}"