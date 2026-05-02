from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app import generate_uuid
from app.events.outbox import LIFECYCLE_STREAM_NAME, list_event_summaries
from app.repositories.events import EventOffsetRepository, EventOutboxRepository


def test_event_offset_repository_upsert_offset(db_session) -> None:
    repository = EventOffsetRepository(db_session)
    first_event_id = generate_uuid()
    second_event_id = generate_uuid()

    created = repository.upsert_offset(
        consumer_group="dashboard",
        stream_name=LIFECYCLE_STREAM_NAME,
        redis_stream_id="1-0",
        last_processed_event_id=first_event_id,
    )
    updated = repository.upsert_offset(
        consumer_group="dashboard",
        stream_name=LIFECYCLE_STREAM_NAME,
        redis_stream_id="2-0",
        last_processed_event_id=second_event_id,
    )

    assert updated.event_offset_id == created.event_offset_id
    assert updated.redis_stream_id == "2-0"
    assert updated.last_processed_event_id == second_event_id


def test_event_listing_returns_api_safe_summary(db_session) -> None:
    repository = EventOutboxRepository(db_session)
    first_event_id = generate_uuid()
    second_event_id = generate_uuid()

    first = repository.enqueue_event(
        event_id=first_event_id,
        schema_version="1.0.0",
        event_type="job.state_changed",
        stream_name=LIFECYCLE_STREAM_NAME,
        producer="processor",
        correlation_id=generate_uuid(),
        idempotency_key="job.state_changed:job-1:1",
        occurred_at=datetime(2026, 5, 1, 10, 0, 0, tzinfo=timezone.utc),
        payload_json={"new_state": "VALIDATING"},
        job_id=generate_uuid(),
        watcher_id=generate_uuid(),
        attempt_number=1,
    )
    second = repository.enqueue_event(
        event_id=second_event_id,
        schema_version="1.0.0",
        event_type="job.registered",
        stream_name=LIFECYCLE_STREAM_NAME,
        producer="watcher",
        correlation_id=generate_uuid(),
        idempotency_key="job.registered:job-2:1",
        occurred_at=datetime(2026, 5, 1, 11, 0, 0, tzinfo=timezone.utc),
        payload_json={"initial_state": "REGISTERED"},
        job_id=generate_uuid(),
        watcher_id=generate_uuid(),
        attempt_number=1,
    )

    items, total = list_event_summaries(repository, limit=10, offset=0)

    assert total == 2
    assert [item.event_id for item in items] == [second_event_id, first_event_id]
    assert items[0].stream_name == LIFECYCLE_STREAM_NAME
    assert set(items[0].model_dump(mode="json")) == {
        "event_id",
        "event_type",
        "schema_version",
        "job_id",
        "watcher_id",
        "producer",
        "occurred_at",
        "stream_name",
        "correlation_id",
    }
    assert "payload_json" not in items[0].model_dump(mode="json")
    assert str(items[0].correlation_id) == str(second.correlation_id)
    assert str(items[1].correlation_id) == str(first.correlation_id)
