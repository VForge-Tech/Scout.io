"""Shared Redis connection pool for the application."""

import redis
from typing import Optional

from app.core.config import get_settings

settings = get_settings()


class RedisPool:
    """Singleton Redis connection pool."""

    _pool: Optional[redis.ConnectionPool] = None
    _client: Optional[redis.Redis] = None

    @classmethod
    def get_pool(cls) -> redis.ConnectionPool:
        """Get or create the connection pool singleton."""
        if cls._pool is None:
            cls._pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                socket_keepalive=True,
                health_check_interval=30,
                decode_responses=False,
            )
        return cls._pool

    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get a Redis client from the pool."""
        if cls._client is None:
            cls._client = redis.Redis(connection_pool=cls.get_pool())
        return cls._client

    @classmethod
    def close(cls):
        """Close the pool and client."""
        if cls._client:
            cls._client.close()
            cls._client = None
        if cls._pool:
            cls._pool.disconnect()
            cls._pool = None


def get_redis_client() -> redis.Redis:
    """Get a Redis client from the shared pool."""
    return RedisPool.get_client()


def get_redis_pool() -> redis.ConnectionPool:
    """Get the shared Redis connection pool."""
    return RedisPool.get_pool()