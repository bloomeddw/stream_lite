from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.events.outbox import (
    LIFECYCLE_STREAM_NAME,
    build_idempotency_key,
    enqueue_event,
    validate_event_payload,
)
from app.repositories.events import EventOutboxRepository


def test_outbox_validates_and_enqueues_schema_valid_event(db_session) -> None:
    valid_payload = _load_event_example("job_state_changed.valid.json")
    validated = validate_event_payload(valid_payload)
    assert validated.event_type == "job.state_changed"

    enqueue_payload = dict(valid_payload)
    enqueue_payload.pop("event_id")
    enqueue_payload.pop("idempotency_key")

    repository = EventOutboxRepository(db_session)
    record = enqueue_event(repository, event_payload=enqueue_payload)

    assert record.status == "pending"
    assert record.stream_name == LIFECYCLE_STREAM_NAME
    assert record.event_type == "job.state_changed"
    assert record.schema_version == "1.0.0"
    assert UUID(str(record.event_id))
    assert record.idempotency_key == build_idempotency_key(
        event_type="job.state_changed",
        job_id=valid_payload["job_id"],
        attempt_number=valid_payload["attempt_number"],
    )
    assert str(record.correlation_id) == valid_payload["correlation_id"]


def test_outbox_rejects_invalid_event_payload(db_session) -> None:
    repository = EventOutboxRepository(db_session)
    invalid_payload = _load_event_example("job_state_changed.invalid.json")

    with pytest.raises(ValidationError):
        enqueue_event(repository, event_payload=invalid_payload)

    assert repository.list_pending_events() == []


def _load_event_example(filename: str) -> dict[str, object]:
    example_path = Path(__file__).resolve().parents[2] / "schemas" / "examples" / "events" / filename
    return json.loads(example_path.read_text(encoding="utf-8"))
