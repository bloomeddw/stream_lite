from __future__ import annotations

import json

from app.events.outbox import LIFECYCLE_STREAM_NAME
from app.events.redis_streams import REDIS_STREAM_PAYLOAD_FIELD, RedisStreamClient


def test_redis_stream_client_publishes_json_to_configured_stream() -> None:
    fake_client = _RecordingRedisClient(return_stream_id=b"1-0")
    stream_client = RedisStreamClient(client=fake_client)
    payload = {"event_type": "job.state_changed", "payload": {"new_state": "VALIDATING"}}

    result = stream_client.publish_json(LIFECYCLE_STREAM_NAME, payload)

    assert result.stream_name == LIFECYCLE_STREAM_NAME
    assert result.stream_id == "1-0"
    assert fake_client.calls == [
        (
            LIFECYCLE_STREAM_NAME,
            {
                REDIS_STREAM_PAYLOAD_FIELD: json.dumps(
                    payload,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            },
        ),
    ]


class _RecordingRedisClient:
    def __init__(self, *, return_stream_id: bytes | str) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []
        self._return_stream_id = return_stream_id

    def xadd(self, stream_name: str, fields: dict[str, str]) -> bytes | str:
        self.calls.append((stream_name, fields))
        return self._return_stream_id
