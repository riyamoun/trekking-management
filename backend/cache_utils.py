"""Redis cache helpers for frequently accessed treks."""

from __future__ import annotations

import json

from flask import current_app

from backend.extensions import redis_client

OPEN_TREKS_KEY = "treks:open"
TREK_DETAIL_PREFIX = "treks:detail:"


def cache_ttl() -> int:
    return int(current_app.config.get("CACHE_TTL_SECONDS", 300))


def get_cached_json(key: str):
    raw = redis_client.get(key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def set_cached_json(key: str, value, ttl: int | None = None) -> None:
    redis_client.setex(key, ttl or cache_ttl(), json.dumps(value, default=str))


def invalidate_trek_caches(trek_id: int | None = None) -> None:
    redis_client.delete(OPEN_TREKS_KEY)
    redis_client.delete_pattern(f"{TREK_DETAIL_PREFIX}*")
    if trek_id is not None:
        redis_client.delete(f"{TREK_DETAIL_PREFIX}{trek_id}")
