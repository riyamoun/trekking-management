"""Shared Flask extensions."""

from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
from redis import Redis


db = SQLAlchemy()
jwt = JWTManager()


class RedisClient:
    """Thin Redis wrapper initialized with the Flask app."""

    def __init__(self) -> None:
        self._client: Redis | None = None

    def init_app(self, app) -> None:
        url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
        self._client = Redis.from_url(url, decode_responses=True)
        try:
            self._client.ping()
        except Exception as exc:  # pragma: no cover - startup diagnostics
            app.logger.warning("Redis unavailable at %s: %s", url, exc)

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis client not initialized")
        return self._client

    def get(self, key: str):
        try:
            return self.client.get(key)
        except Exception:
            return None

    def setex(self, key: str, ttl: int, value: str) -> bool:
        try:
            self.client.setex(key, ttl, value)
            return True
        except Exception:
            return False

    def delete(self, *keys: str) -> None:
        try:
            if keys:
                self.client.delete(*keys)
        except Exception:
            pass

    def delete_pattern(self, pattern: str) -> None:
        try:
            for key in self.client.scan_iter(match=pattern):
                self.client.delete(key)
        except Exception:
            pass


redis_client = RedisClient()
