"""Dependency health checks shared by /health/ready and the metrics sampler.

Centralises the Postgres / Redis / Qdrant connectivity checks so the readiness
endpoint and the Prometheus dependency-health gauge stay in sync.
"""


def check_dependencies() -> dict[str, str]:
    """Return {service: status} where status is "ok" or an error string."""
    from app.core.config import get_settings
    from app.db.session import SessionLocal

    settings = get_settings()
    services: dict[str, str] = {"self": "ok"}

    try:
        from sqlalchemy import text

        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        services["database"] = "ok"
    except Exception as e:  # noqa: BLE001
        services["database"] = f"error: {e}"

    if not settings.redis_url:
        services["redis"] = "skipped"
    else:
        try:
            import redis

            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            r.close()
            services["redis"] = "ok"
        except Exception as e:  # noqa: BLE001
            services["redis"] = f"error: {e}"

    if not settings.qdrant_enabled or not settings.qdrant_url:
        services["qdrant"] = "skipped"
    else:
        try:
            from qdrant_client import QdrantClient

            qdrant = QdrantClient(url=settings.qdrant_url)
            qdrant.get_collections()
            services["qdrant"] = "ok"
        except Exception as e:  # noqa: BLE001
            services["qdrant"] = f"error: {e}"

    return services


def dependencies_healthy() -> bool:
    """True when every required dependency reports ok.

    Services skipped because their feature is disabled (e.g. Qdrant when
    ``qdrant_enabled=false``) are not considered failures.
    """
    return all(v in ("ok", "skipped") for v in check_dependencies().values())