"""Schema-validated event outbox enqueue and listing primitives."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID

from app import generate_uuid
from app.api.schemas.api_models import EventListItem
from app.events.models import (
    DeliveryCompletedEvent,
    DeliveryFailedEvent,
    DeliveryStartedEvent,
    FileDetectedEvent,
    FileQuarantinedEvent,
    FileStableEvent,
    FileValidatedEvent,
    JobCompletedEvent,
    JobFailedEvent,
    JobRegisteredEvent,
    JobStateChangedEvent,
    ProcessingCompletedEvent,
    ProcessingFailedEvent,
    ProcessingStartedEvent,
    RetryScheduledEvent,
)
from app.repositories.events import EventOutboxRepository

LIFECYCLE_STREAM_NAME = "stream_lite.lifecycle"
DEAD_LETTER_STREAM_NAME = "stream_lite.dead_letter"

_EVENT_MODEL_BY_EVENT_TYPE = {
    "delivery.completed": DeliveryCompletedEvent,
    "delivery.failed": DeliveryFailedEvent,
    "delivery.started": DeliveryStartedEvent,
    "file.detected": FileDetectedEvent,
    "file.quarantined": FileQuarantinedEvent,
    "file.stable": FileStableEvent,
    "file.validated": FileValidatedEvent,
    "job.completed": JobCompletedEvent,
    "job.failed": JobFailedEvent,
    "job.registered": JobRegisteredEvent,
    "job.state_changed": JobStateChangedEvent,
    "processing.completed": ProcessingCompletedEvent,
    "processing.failed": ProcessingFailedEvent,
    "processing.started": ProcessingStartedEvent,
    "retry.scheduled": RetryScheduledEvent,
}


def event_model_for_type(event_type: str):
    """Return the authoritative WP-02 model for an event type."""

    try:
        return _EVENT_MODEL_BY_EVENT_TYPE[event_type]
    except KeyError as exc:
        raise ValueError(f"unsupported event type: {event_type}") from exc


def build_idempotency_key(
    *,
    event_type: str,
    job_id: UUID | str | None,
    attempt_number: int | None,
) -> str:
    """Build the documented event idempotency key shape used by fixtures."""

    job_component = "none" if job_id is None else str(job_id)
    attempt_component = "none" if attempt_number is None else str(attempt_number)
    return f"{event_type}:{job_component}:{attempt_component}"


def validate_event_payload(event_payload: Mapping[str, Any]) -> Any:
    """Validate a lifecycle event payload against the matching WP-02 model."""

    payload_dict = dict(event_payload)
    event_type = payload_dict.get("event_type")
    if not isinstance(event_type, str) or not event_type:
        raise ValueError("event_type is required for event validation")
    model = event_model_for_type(event_type)
    return model.model_validate(payload_dict)


def enqueue_event(
    repository: EventOutboxRepository,
    *,
    event_payload: Mapping[str, Any],
    event_id: UUID | str | None = None,
    stream_name: str = LIFECYCLE_STREAM_NAME,
    idempotency_key: str | None = None,
):
    """Validate and persist an outbox row without publishing it."""

    payload_dict = dict(event_payload)
    resolved_event_id = event_id or payload_dict.get("event_id") or generate_uuid()
    payload_dict["event_id"] = str(resolved_event_id)

    if idempotency_key is not None:
        payload_dict["idempotency_key"] = idempotency_key
    elif "idempotency_key" not in payload_dict or not payload_dict["idempotency_key"]:
        payload_dict["idempotency_key"] = build_idempotency_key(
            event_type=str(payload_dict["event_type"]),
            job_id=_uuid_or_none(payload_dict.get("job_id")),
            attempt_number=_int_or_none(payload_dict.get("attempt_number")),
        )

    validated_event = validate_event_payload(payload_dict)
    return repository.enqueue_event(
        event_id=validated_event.event_id,
        schema_version=validated_event.schema_version,
        event_type=validated_event.event_type,
        stream_name=stream_name or LIFECYCLE_STREAM_NAME,
        producer=validated_event.producer,
        correlation_id=validated_event.correlation_id,
        idempotency_key=validated_event.idempotency_key,
        occurred_at=_parse_rfc3339_utc(validated_event.occurred_at),
        payload_json=validated_event.payload.model_dump(mode="json"),
        status="pending",
        job_id=validated_event.job_id,
        watcher_id=validated_event.watcher_id,
        attempt_number=validated_event.attempt_number,
    )


def list_event_summaries(
    repository: EventOutboxRepository,
    *,
    watcher_id: UUID | str | None = None,
    job_id: UUID | str | None = None,
    event_type: str | None = None,
    from_occurred_at: datetime | None = None,
    to_occurred_at: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[EventListItem], int]:
    """Return API-safe event summaries backed by persisted outbox rows."""

    rows, total = repository.list_events(
        watcher_id=watcher_id,
        job_id=job_id,
        event_type=event_type,
        from_occurred_at=from_occurred_at,
        to_occurred_at=to_occurred_at,
        limit=limit,
        offset=offset,
    )
    items = [
        EventListItem(
            event_id=row.event_id,
            event_type=row.event_type,
            schema_version=row.schema_version,
            job_id=row.job_id,
            watcher_id=row.watcher_id,
            producer=row.producer,
            occurred_at=_format_rfc3339_utc(row.occurred_at),
            stream_name=row.stream_name,
            correlation_id=row.correlation_id,
        )
        for row in rows
    ]
    return items, total


def _parse_rfc3339_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _format_rfc3339_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _int_or_none(value: Any) -> int | None:
    return None if value is None else int(value)


def _uuid_or_none(value: Any) -> UUID | str | None:
    return value


__all__ = [
    "DEAD_LETTER_STREAM_NAME",
    "LIFECYCLE_STREAM_NAME",
    "build_idempotency_key",
    "enqueue_event",
    "event_model_for_type",
    "list_event_summaries",
    "validate_event_payload",
]
