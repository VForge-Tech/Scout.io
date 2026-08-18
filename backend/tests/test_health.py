"""Tests for the dependency health checks (/health/ready support)."""

from unittest.mock import patch

from app.core.health import check_dependencies, dependencies_healthy


class TestCheckDependencies:
    def test_qdrant_skipped_when_disabled(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.config.get_settings",
            lambda: _settings(qdrant_enabled=False),
        )
        with patch("app.db.session.SessionLocal"):
            with patch("redis.from_url") as mock_from_url:
                mock_from_url.return_value.ping.return_value = True
                deps = check_dependencies()
                assert deps["qdrant"] == "skipped"
                assert deps["database"] == "ok"
                assert deps["redis"] == "ok"
                assert dependencies_healthy()

    def test_qdrant_checked_when_enabled(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.config.get_settings",
            lambda: _settings(qdrant_enabled=True),
        )
        with patch("app.db.session.SessionLocal"):
            with patch("redis.from_url"):
                with patch("qdrant_client.QdrantClient") as mock_client:
                    mock_client.return_value.get_collections.return_value = None
                    deps = check_dependencies()
                    assert deps["qdrant"] == "ok"

    def test_redis_skipped_when_no_url(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.config.get_settings",
            lambda: _settings(redis_url=""),
        )
        with patch("app.db.session.SessionLocal"):
            deps = check_dependencies()
            assert deps["redis"] == "skipped"

    def test_disabled_service_not_a_failure(self, monkeypatch):
        monkeypatch.setattr(
            "app.core.config.get_settings",
            lambda: _settings(qdrant_enabled=False),
        )
        with patch("app.db.session.SessionLocal"):
            with patch("redis.from_url") as mock_from_url:
                mock_from_url.return_value.ping.return_value = True
                assert dependencies_healthy()


def _settings(qdrant_enabled=True, redis_url="redis://localhost:6379/0"):
    from types import SimpleNamespace

    return SimpleNamespace(
        qdrant_enabled=qdrant_enabled,
        qdrant_url="http://localhost:6333",
        redis_url=redis_url,
    )