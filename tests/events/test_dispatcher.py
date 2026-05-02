from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.events.dispatcher import EVENT_DISPATCHER_SERVICE, EventDispatcher
from app.events.outbox import DEAD_LETTER_STREAM_NAME, LIFECYCLE_STREAM_NAME, enqueue_event
from app.events.redis_streams import RedisStreamClient
from app.repositories.events import EventOutboxRepository


def test_dispatcher_publishes_due_event_and_marks_published(db_session) -> None:
    repository = EventOutboxRepository(db_session)
    record = enqueue_event(
        repository,
        event_payload=_load_event_example("job_state_changed.valid.json"),
    )
    fake_client = _BehaviorRedisClient()
    dispatcher = EventDispatcher(
        outbox_repository=repository,
        stream_client=RedisStreamClient(client=fake_client),
    )
    published_at = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

    dispatcher.publish_due_events(as_of=published_at)
    db_session.refresh(record)

    assert record.status == "published"
    assert record.published_stream_id == "1-0"
    assert _as_utc(record.published_at) == published_at


def test_dispatcher_marks_publish_failed_before_dead_letter_threshold(db_session) -> None:
    repository = EventOutboxRepository(db_session)
    record = enqueue_event(
        repository,
        event_payload=_load_event_example("job_state_changed.valid.json"),
    )
    fake_client = _BehaviorRedisClient(fail_streams={LIFECYCLE_STREAM_NAME})
    dispatcher = EventDispatcher(
        outbox_repository=repository,
        stream_client=RedisStreamClient(client=fake_client),
    )
    failed_at = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)

    dispatcher.publish_due_events(as_of=failed_at)
    db_session.refresh(record)

    assert record.status == "publish_failed"
    assert record.publish_attempts == 1
    assert record.last_error_code == "BROKER_UNAVAILABLE"
    assert _as_utc(record.next_publish_at) == failed_at + timedelta(seconds=1)
    assert [call["stream_name"] for call in fake_client.calls] == [LIFECYCLE_STREAM_NAME]


def test_dispatcher_dead_letters_on_third_failure(db_session) -> None:
    repository = EventOutboxRepository(db_session)
    record = enqueue_event(
        repository,
        event_payload=_load_event_example("job_state_changed.valid.json"),
    )
    record.status = "publish_failed"
    record.publish_attempts = 2
    record.next_publish_at = datetime(2026, 5, 1, 11, 59, 0, tzinfo=timezone.utc)
    db_session.flush()

    fake_client = _BehaviorRedisClient(fail_streams={LIFECYCLE_STREAM_NAME})
    dispatcher = EventDispatcher(
        outbox_repository=repository,
        stream_client=RedisStreamClient(client=fake_client),
    )

    dispatcher.publish_due_events(as_of=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc))
    db_session.refresh(record)

    assert record.status == "dead_lettered"
    assert record.publish_attempts == 3
    assert record.last_error_code == "BROKER_UNAVAILABLE"
    assert [call["stream_name"] for call in fake_client.calls] == [
        LIFECYCLE_STREAM_NAME,
        DEAD_LETTER_STREAM_NAME,
    ]

    dead_letter_payload = fake_client.calls[-1]["payload"]
    assert dead_letter_payload["original_event_id"] == str(record.event_id)
    assert dead_letter_payload["consumer"] == EVENT_DISPATCHER_SERVICE
    assert dead_letter_payload["failure_code"] == "BROKER_UNAVAILABLE"
    assert dead_letter_payload["attempt_count"] == 3
    assert dead_letter_payload["last_error_message"] == "simulated publish failure"


def _load_event_example(filename: str) -> dict[str, object]:
    example_path = Path(__file__).resolve().parents[2] / "schemas" / "examples" / "events" / filename
    return json.loads(example_path.read_text(encoding="utf-8"))


class _BehaviorRedisClient:
    def __init__(self, *, fail_streams: set[str] | None = None) -> None:
        self.calls: list[dict[str, object]] = []
        self._fail_streams = fail_streams or set()

    def xadd(self, stream_name: str, fields: dict[str, str]) -> str:
        payload = json.loads(fields["payload_json"])
        self.calls.append({"stream_name": stream_name, "payload": payload})
        if stream_name in self._fail_streams:
            raise RuntimeError("simulated publish failure")
        return f"{len(self.calls)}-0"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
