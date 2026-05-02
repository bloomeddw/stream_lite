"""Pydantic models bound to the documented event JSON schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, StringConstraints
from typing_extensions import Annotated

from app._schema_types import (
    ErrorCode,
    Rfc3339Utc,
    RouteTag,
    SafeDisplayPath,
    SafeLocator,
    SchemaModel,
    SchemaVersion,
    Sha256Hex,
)

ActorService = Literal[
    "api",
    "watcher",
    "validator",
    "processor",
    "delivery",
    "retry_scheduler",
    "event_dispatcher",
    "streamlit",
]
JobState = Literal[
    "DETECTED",
    "STABILIZING",
    "REGISTERED",
    "VALIDATING",
    "VALIDATED",
    "INVALID",
    "QUARANTINED",
    "PROCESSING",
    "PROCESSED",
    "DELIVERING",
    "DELIVERED",
    "RETRY_PENDING",
    "FAILED",
    "COMPLETED",
    "COMPLETED_WITH_DELIVERY_ERRORS",
]
ProcessingEngine = Literal["spark", "flink"]
FailureClass = Literal["retryable", "non_retryable"]
RetryStage = Literal["validation", "processing", "delivery"]


class EventEnvelopeModel(SchemaModel):
    schema_version: SchemaVersion
    event_id: UUID
    idempotency_key: Annotated[str, StringConstraints(min_length=8, max_length=256)]
    correlation_id: UUID
    occurred_at: Rfc3339Utc
    job_id: UUID | None
    watcher_id: UUID | None
    attempt_number: Annotated[int | None, Field(ge=0)]


class FileDetectedPayload(SchemaModel):
    file_id: UUID
    source_folder_id: UUID
    source_display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1, max_length=1024)]
    size_bytes: Annotated[int, Field(ge=0)]
    observed_at: Rfc3339Utc
    deduplication_key: Annotated[str, StringConstraints(min_length=8, max_length=256)]


class FileDetectedEvent(EventEnvelopeModel):
    event_type: Literal["file.detected"]
    producer: Literal["watcher"]
    payload: FileDetectedPayload


class FileStablePayload(SchemaModel):
    file_id: UUID
    source_display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1, max_length=1024)]
    size_bytes: Annotated[int, Field(ge=0)]
    sha256: Sha256Hex
    stable_after_seconds: Annotated[float, Field(ge=0)]


class FileStableEvent(EventEnvelopeModel):
    event_type: Literal["file.stable"]
    producer: Literal["watcher"]
    payload: FileStablePayload


class JobRegisteredPayload(SchemaModel):
    file_id: UUID
    source_folder_id: UUID
    initial_state: Literal["REGISTERED"]
    route_policy: Literal["tag_match_all_destinations"]
    candidate_destination_count: Annotated[int, Field(ge=0)]


class JobRegisteredEvent(EventEnvelopeModel):
    event_type: Literal["job.registered"]
    producer: Literal["watcher"]
    payload: JobRegisteredPayload


class JobStateChangedPayload(SchemaModel):
    previous_state: JobState | None
    new_state: JobState
    transition_reason: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    stage_owner: ActorService


class JobStateChangedEvent(EventEnvelopeModel):
    event_type: Literal["job.state_changed"]
    producer: Literal["processor"]
    payload: JobStateChangedPayload


class FileValidatedPayload(SchemaModel):
    file_id: UUID
    validation_status: Literal["valid"]
    rules_applied: list[Annotated[str, StringConstraints(min_length=1, max_length=64)]]
    duration_seconds: Annotated[float, Field(ge=0)]


class FileValidatedEvent(EventEnvelopeModel):
    event_type: Literal["file.validated"]
    producer: Literal["validator"]
    payload: FileValidatedPayload


class FileQuarantinedPayload(SchemaModel):
    file_id: UUID
    validation_status: Literal["quarantined"]
    reason_codes: Annotated[list[ErrorCode], Field(min_length=1)]
    quarantine_record_id: UUID
    quarantine_locator: Annotated[SafeLocator, StringConstraints(min_length=1, max_length=1024)]
    operator_message: Annotated[str, StringConstraints(min_length=1, max_length=512)]


class FileQuarantinedEvent(EventEnvelopeModel):
    event_type: Literal["file.quarantined"]
    producer: Literal["validator"]
    payload: FileQuarantinedPayload


class ProcessingStartedPayload(SchemaModel):
    engine: ProcessingEngine
    engine_version: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    input_locator: Annotated[SafeLocator, StringConstraints(min_length=1, max_length=1024)]
    started_at: Rfc3339Utc


class ProcessingStartedEvent(EventEnvelopeModel):
    event_type: Literal["processing.started"]
    producer: Literal["processor"]
    payload: ProcessingStartedPayload


class ProcessingCompletedPayload(SchemaModel):
    engine: ProcessingEngine
    output_manifest_id: UUID
    output_locator: Annotated[SafeLocator, StringConstraints(min_length=1, max_length=1024)]
    input_rows: Annotated[int | None, Field(ge=0)]
    output_rows: Annotated[int | None, Field(ge=0)]
    duration_seconds: Annotated[float, Field(ge=0)]


class ProcessingCompletedEvent(EventEnvelopeModel):
    event_type: Literal["processing.completed"]
    producer: Literal["processor"]
    payload: ProcessingCompletedPayload


class ProcessingFailedPayload(SchemaModel):
    engine: ProcessingEngine
    failure_class: FailureClass
    error_code: ErrorCode
    operator_message: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    retryable: bool


class ProcessingFailedEvent(EventEnvelopeModel):
    event_type: Literal["processing.failed"]
    producer: Literal["processor"]
    payload: ProcessingFailedPayload


class DeliveryStartedPayload(SchemaModel):
    destination_folder_id: UUID
    destination_display_path: Annotated[
        SafeDisplayPath,
        StringConstraints(min_length=1, max_length=1024),
    ]
    matched_tags: list[RouteTag]
    output_manifest_id: UUID
    started_at: Rfc3339Utc


class DeliveryStartedEvent(EventEnvelopeModel):
    event_type: Literal["delivery.started"]
    producer: Literal["delivery"]
    payload: DeliveryStartedPayload


class DeliveryCompletedPayload(SchemaModel):
    destination_folder_id: UUID
    destination_display_path: Annotated[
        SafeDisplayPath,
        StringConstraints(min_length=1, max_length=1024),
    ]
    output_manifest_id: UUID
    bytes_written: Annotated[int, Field(ge=0)]
    completed_at: Rfc3339Utc
    duration_seconds: Annotated[float, Field(ge=0)]


class DeliveryCompletedEvent(EventEnvelopeModel):
    event_type: Literal["delivery.completed"]
    producer: Literal["delivery"]
    payload: DeliveryCompletedPayload


class DeliveryFailedPayload(SchemaModel):
    destination_folder_id: UUID
    destination_display_path: Annotated[
        SafeDisplayPath,
        StringConstraints(min_length=1, max_length=1024),
    ]
    failure_class: FailureClass
    error_code: ErrorCode
    operator_message: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    retryable: bool


class DeliveryFailedEvent(EventEnvelopeModel):
    event_type: Literal["delivery.failed"]
    producer: Literal["delivery"]
    payload: DeliveryFailedPayload


class RetryScheduledPayload(SchemaModel):
    next_stage: RetryStage
    due_at: Rfc3339Utc
    backoff_seconds: Annotated[float, Field(ge=0)]
    max_attempts: Annotated[int, Field(ge=1)]
    retry_reason: Annotated[str, StringConstraints(min_length=1, max_length=256)]


class RetryScheduledEvent(EventEnvelopeModel):
    event_type: Literal["retry.scheduled"]
    producer: Literal["retry_scheduler"]
    payload: RetryScheduledPayload


class JobCompletedPayload(SchemaModel):
    final_state: Literal["COMPLETED", "COMPLETED_WITH_DELIVERY_ERRORS"]
    successful_destination_count: Annotated[int, Field(ge=0)]
    failed_destination_count: Annotated[int, Field(ge=0)]
    completed_at: Rfc3339Utc


class JobCompletedEvent(EventEnvelopeModel):
    event_type: Literal["job.completed"]
    producer: Literal["delivery"]
    payload: JobCompletedPayload


class JobFailedPayload(SchemaModel):
    final_failure_class: Literal["non_retryable", "exhausted_retries"]
    exhausted_stage: Literal["validation", "processing", "delivery", "routing"]
    last_error_code: ErrorCode
    operator_message: Annotated[str, StringConstraints(min_length=1, max_length=512)]


class JobFailedEvent(EventEnvelopeModel):
    event_type: Literal["job.failed"]
    producer: Literal["retry_scheduler"]
    payload: JobFailedPayload


EVENT_MODEL_BY_SCHEMA_NAME = {
    "delivery_completed": DeliveryCompletedEvent,
    "delivery_failed": DeliveryFailedEvent,
    "delivery_started": DeliveryStartedEvent,
    "file_detected": FileDetectedEvent,
    "file_quarantined": FileQuarantinedEvent,
    "file_stable": FileStableEvent,
    "file_validated": FileValidatedEvent,
    "job_completed": JobCompletedEvent,
    "job_failed": JobFailedEvent,
    "job_registered": JobRegisteredEvent,
    "job_state_changed": JobStateChangedEvent,
    "processing_completed": ProcessingCompletedEvent,
    "processing_failed": ProcessingFailedEvent,
    "processing_started": ProcessingStartedEvent,
    "retry_scheduled": RetryScheduledEvent,
}


__all__ = [
    "DeliveryCompletedEvent",
    "DeliveryFailedEvent",
    "DeliveryStartedEvent",
    "EVENT_MODEL_BY_SCHEMA_NAME",
    "FileDetectedEvent",
    "FileQuarantinedEvent",
    "FileStableEvent",
    "FileValidatedEvent",
    "JobCompletedEvent",
    "JobFailedEvent",
    "JobRegisteredEvent",
    "JobStateChangedEvent",
    "ProcessingCompletedEvent",
    "ProcessingFailedEvent",
    "ProcessingStartedEvent",
    "RetryScheduledEvent",
]
