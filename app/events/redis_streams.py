"""Redis Streams publication primitives for WP-04."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

REDIS_STREAM_PAYLOAD_FIELD = "payload_json"


@dataclass(frozen=True, slots=True)
class RedisPublishResult:
    stream_name: str
    stream_id: str


class RedisStreamClient:
    """Small wrapper around Redis Streams XADD publication."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        redis_url: str | None = None,
    ) -> None:
        if client is None and not redis_url:
            raise ValueError("redis_url is required when a Redis client is not injected")
        self._client = client
        self._redis_url = redis_url

    @property
    def client(self) -> Any:
        if self._client is None:
            self._client = self._build_client(self._redis_url)
        return self._client

    def publish_json(self, stream_name: str, payload: Mapping[str, Any]) -> RedisPublishResult:
        stream_id = self.client.xadd(
            stream_name,
            {REDIS_STREAM_PAYLOAD_FIELD: json.dumps(dict(payload), separators=(",", ":"), sort_keys=True)},
        )
        if isinstance(stream_id, bytes):
            stream_id = stream_id.decode("utf-8")
        return RedisPublishResult(stream_name=stream_name, stream_id=str(stream_id))

    @staticmethod
    def _build_client(redis_url: str | None) -> Any:
        if not redis_url:
            raise ValueError("redis_url is required when a Redis client is not injected")
        try:
            import redis
        except Exception as exc:  # pragma: no cover - exercised only when runtime dep missing
            raise RuntimeError(
                "RedisStreamClient requires the `redis` package when no client is injected.",
            ) from exc
        return redis.from_url(redis_url, decode_responses=True)


__all__ = [
    "REDIS_STREAM_PAYLOAD_FIELD",
    "RedisPublishResult",
    "RedisStreamClient",
]
