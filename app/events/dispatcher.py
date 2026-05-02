"""Callable outbox dispatcher primitives for WP-04."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.observability.logging import emit_structured_log
from app.repositories.events import EventOutboxRepository

from .outbox import DEAD_LETTER_STREAM_NAME
from .redis_streams import RedisPublishResult, RedisStreamClient

EVENT_DISPATCHER_SERVICE = "event_dispatcher"
MAX_PUBLISH_ATTEMPTS = 3


class EventDispatcher:
    """Publish pending outbox rows to Redis Streams."""

    def __init__(
        self,
        *,
        outbox_repository: EventOutboxRepository,
        stream_client: RedisStreamClient,
        logger: logging.Logger | None = None,
    ) -> None:
        self._outbox_repository = outbox_repository
        self._stream_client = stream_client
        self._logger = logger or _default_logger()

    def publish_due_events(
        self,
        limit: int = 100,
        as_of: datetime | None = None,
    ) -> list[Any]:
        dispatch_time = as_of or self._now()
        records = self._outbox_repository.claim_due_events(as_of=dispatch_time, limit=limit)
        return [self._publish_record(record, dispatch_time) for record in records]

    def publish_one(self, record) -> Any:
        return self._publish_record(record, self._now())

    def mark_publish_failure(
        self,
        record,
        error_code: str,
        message: str,
        as_of: datetime | None = None,
    ) -> Any:
        failed_at = as_of or self._now()
        next_attempt = record.publish_attempts + 1
        if next_attempt >= MAX_PUBLISH_ATTEMPTS:
            return self.dead_letter_record(record, error_code, message)

        failed_record = self._outbox_repository.mark_publish_failed(
            record.outbox_id,
            last_error_code=error_code,
            next_publish_at=failed_at + timedelta(seconds=next_attempt),
        )
        self._emit_log(
            level="ERROR",
            event="outbox_publication_failure",
            message="Outbox publication failed; retry scheduled.",
            record=failed_record,
            error_code=error_code,
        )
        return failed_record

    def dead_letter_record(self, record, failure_code: str, message: str) -> Any:
        dead_lettered = self._outbox_repository.mark_dead_lettered(
            record.outbox_id,
            last_error_code=failure_code,
            next_publish_at=None,
        )
        payload = {
            "original_event_id": str(record.event_id),
            "consumer": EVENT_DISPATCHER_SERVICE,
            "failure_code": failure_code,
            "attempt_count": dead_lettered.publish_attempts,
            "last_error_message": message,
        }
        try:
            self._stream_client.publish_json(DEAD_LETTER_STREAM_NAME, payload)
        except Exception:
            self._emit_log(
                level="ERROR",
                event="outbox_dead_letter_publish_failure",
                message="Dead-letter publication failed after outbox exhaustion.",
                record=dead_lettered,
                error_code=failure_code,
            )
        else:
            self._emit_log(
                level="ERROR",
                event="outbox_dead_lettered",
                message="Outbox record reached the dead-letter threshold.",
                record=dead_lettered,
                error_code=failure_code,
            )
        return dead_lettered

    def _publish_record(self, record, as_of: datetime) -> Any:
        try:
            publish_result = self._stream_client.publish_json(
                record.stream_name,
                _event_envelope_from_record(record),
            )
        except Exception as exc:
            error_code = _error_code_from_exception(exc)
            message = str(exc) or exc.__class__.__name__
            return self.mark_publish_failure(record, error_code, message, as_of=as_of)

        published = self._outbox_repository.mark_published(
            record.outbox_id,
            published_stream_id=publish_result.stream_id,
            published_at=as_of,
        )
        self._emit_log(
            event="outbox_publication_success",
            message="Outbox record published to Redis Streams.",
            record=published,
        )
        return published

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _emit_log(
        self,
        *,
        event: str,
        message: str,
        record,
        level: str = "INFO",
        error_code: str | None = None,
    ) -> None:
        emit_structured_log(
            self._logger,
            service=EVENT_DISPATCHER_SERVICE,
            component="app.events.dispatcher",
            event=event,
            message=message,
            level=level,
            correlation_id=str(record.correlation_id),
            job_id=None if record.job_id is None else str(record.job_id),
            watcher_id=None if record.watcher_id is None else str(record.watcher_id),
            event_type=record.event_type,
            error_code=error_code,
        )


def _default_logger() -> logging.Logger:
    logger = logging.getLogger("stream_lite.event_dispatcher")
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


def _error_code_from_exception(exc: Exception) -> str:
    error_code = getattr(exc, "error_code", None)
    if isinstance(error_code, str) and error_code:
        return error_code
    return "BROKER_UNAVAILABLE"


def _event_envelope_from_record(record) -> dict[str, object]:
    return {
        "schema_version": record.schema_version,
        "event_type": record.event_type,
        "event_id": str(record.event_id),
        "idempotency_key": record.idempotency_key,
        "correlation_id": str(record.correlation_id),
        "occurred_at": record.occurred_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "producer": record.producer,
        "job_id": None if record.job_id is None else str(record.job_id),
        "watcher_id": None if record.watcher_id is None else str(record.watcher_id),
        "attempt_number": record.attempt_number,
        "payload": dict(record.payload_json),
    }


__all__ = [
    "EVENT_DISPATCHER_SERVICE",
    "EventDispatcher",
]
