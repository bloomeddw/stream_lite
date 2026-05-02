from __future__ import annotations

from datetime import datetime, timezone

from app import generate_uuid
from app.events.outbox import LIFECYCLE_STREAM_NAME
from app.repositories.events import EventOutboxRepository


def test_event_outbox_enqueue_and_mark_dispatched(db_session) -> None:
    repo = EventOutboxRepository(db_session)
    event = repo.enqueue_event(
        outbox_id=generate_uuid(),
        event_id=generate_uuid(),
        schema_version="1.0.0",
        event_type="job.state_changed",
        stream_name=LIFECYCLE_STREAM_NAME,
        producer="processor",
        correlation_id=generate_uuid(),
        idempotency_key="job.state_changed:job-1:1:none",
        occurred_at=datetime(2026, 4, 30, 9, 0, 0, tzinfo=timezone.utc),
        payload_json={
            "previous_state": "REGISTERED",
            "new_state": "VALIDATING",
            "transition_reason": "VALIDATION_STARTED",
            "stage_owner": "validator",
        },
    )

    pending = repo.list_pending_events()
    assert [row.outbox_id for row in pending] == [event.outbox_id]

    repo.mark_dispatched(event.outbox_id, published_stream_id="1714467600-0")
    db_session.refresh(event)

    assert event.status == "published"
    assert event.published_stream_id == "1714467600-0"
    assert event.next_publish_at is None
