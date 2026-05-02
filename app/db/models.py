"""SQLAlchemy durable-state models for Stream Lite WP-03."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _json_payload_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _string_list_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.ARRAY(sa.Text()), "postgresql")


WATCHER_LIFECYCLE_STATE = sa.Enum(
    "CREATED",
    "ACTIVE",
    "PAUSED",
    "STOPPING",
    "STOPPED",
    "ERROR",
    name="watcher_lifecycle_state",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
OPERATIONAL_STATUS = sa.Enum(
    "green",
    "yellow",
    "red",
    name="operational_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
ROUTE_POLICY = sa.Enum(
    "tag_match_all_destinations",
    name="route_policy",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
JOB_STATE = sa.Enum(
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
    name="job_state",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
ACTOR_SERVICE = sa.Enum(
    "api",
    "watcher",
    "validator",
    "processor",
    "delivery",
    "retry_scheduler",
    "event_dispatcher",
    "streamlit",
    name="actor_service",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
FAILURE_CLASS = sa.Enum(
    "retryable",
    "non_retryable",
    name="failure_class",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
RETRY_STAGE = sa.Enum(
    "validation",
    "processing",
    "delivery",
    name="retry_stage",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
STAGE_NAME = sa.Enum(
    "validation",
    "processing",
    "delivery",
    "retry",
    "outbox",
    name="stage_name",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
COMMAND_STATUS = sa.Enum(
    "accepted",
    "running",
    "succeeded",
    "failed",
    "expired",
    name="command_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
OUTBOX_STATUS = sa.Enum(
    "pending",
    "published",
    "publish_failed",
    "dead_lettered",
    name="outbox_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
COPY_STATUS = sa.Enum(
    "copied",
    "copy_failed",
    "not_copied_security_block",
    name="copy_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
CLAIM_STATUS = sa.Enum(
    "active",
    "released",
    "expired",
    name="claim_status",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
HEALTH_FOLDER_ROLE = sa.Enum(
    "source",
    "destination",
    name="health_folder_role",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)
PROCESSING_ENGINE = sa.Enum(
    "spark",
    name="processing_engine",
    native_enum=False,
    create_constraint=True,
    validate_strings=True,
)

TERMINAL_JOB_STATES = {
    "COMPLETED",
    "COMPLETED_WITH_DELIVERY_ERRORS",
    "FAILED",
    "QUARANTINED",
}

ALL_TABLE_NAMES = (
    "watchers",
    "watcher_sources",
    "watcher_destinations",
    "watcher_route_matches",
    "control_commands",
    "files",
    "jobs",
    "job_state_history",
    "validation_attempts",
    "processing_attempts",
    "delivery_attempts",
    "output_manifests",
    "retry_schedules",
    "event_outbox",
    "event_offsets",
    "idempotency_keys",
    "stage_ownership_claims",
    "duplicate_suppression_observations",
    "quarantine_records",
    "operational_log_summaries",
    "health_observations",
)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )


class UpdatedAtMixin:
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class WatcherModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "watchers"
    __table_args__ = (
        sa.Index("ix_watchers_lifecycle_state_operational_status", "lifecycle_state", "operational_status"),
    )

    watcher_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(sa.Text(), nullable=False, unique=True)
    lifecycle_state: Mapped[str] = mapped_column(WATCHER_LIFECYCLE_STATE, nullable=False)
    operational_status: Mapped[str] = mapped_column(OPERATIONAL_STATUS, nullable=False)
    route_policy: Mapped[str] = mapped_column(ROUTE_POLICY, nullable=False)
    enabled: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, default=False)
    latest_route_preview_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class WatcherSourceModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "watcher_sources"
    __table_args__ = (
        sa.Index("ix_watcher_sources_watcher_id", "watcher_id"),
        sa.UniqueConstraint("watcher_id", "normalized_path", name="uq_watcher_sources_watcher_id_normalized_path"),
    )

    source_folder_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    watcher_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"),
        nullable=False,
    )
    display_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    normalized_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    route_tags: Mapped[list[str]] = mapped_column(_string_list_type(), nullable=False)
    route_tags_text: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    health_status: Mapped[str] = mapped_column(OPERATIONAL_STATUS, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(sa.String(64))
    enabled: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, default=True)


class WatcherDestinationModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "watcher_destinations"
    __table_args__ = (
        sa.Index("ix_watcher_destinations_watcher_id", "watcher_id"),
        sa.UniqueConstraint("watcher_id", "normalized_path", name="uq_watcher_destinations_watcher_id_normalized_path"),
    )

    destination_folder_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    watcher_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"),
        nullable=False,
    )
    display_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    normalized_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    route_tags: Mapped[list[str]] = mapped_column(_string_list_type(), nullable=False)
    route_tags_text: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    health_status: Mapped[str] = mapped_column(OPERATIONAL_STATUS, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(sa.String(64))
    enabled: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, default=True)


class WatcherRouteMatchModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "watcher_route_matches"
    __table_args__ = (
        sa.Index("ix_watcher_route_matches_watcher_id", "watcher_id"),
    )

    route_match_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    watcher_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_folder_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watcher_sources.source_folder_id", ondelete="CASCADE"),
        nullable=False,
    )
    destination_folder_id: Mapped[UUID | None] = mapped_column(
        sa.ForeignKey("watcher_destinations.destination_folder_id", ondelete="CASCADE"),
    )
    route_policy: Mapped[str] = mapped_column(ROUTE_POLICY, nullable=False)
    matched_route_tags: Mapped[list[str]] = mapped_column(_string_list_type(), nullable=False)
    unmatched_reason_code: Mapped[str | None] = mapped_column(sa.String(64))


class ControlCommandModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "control_commands"

    command_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    command_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    target_resource_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    target_resource_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)
    requested_by: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    operator_reason: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    status: Mapped[str] = mapped_column(COMMAND_STATUS, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    result_locator: Mapped[str | None] = mapped_column(sa.String(1024))
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)


class FileModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "files"
    __table_args__ = (
        sa.Index("ix_files_watcher_id_source_folder_id", "watcher_id", "source_folder_id"),
        sa.UniqueConstraint("deduplication_key", name="uq_files_deduplication_key"),
    )

    file_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    watcher_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_folder_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watcher_sources.source_folder_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_display_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    source_container_locator: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    sha256: Mapped[str | None] = mapped_column(sa.String(64))
    first_seen_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    stable_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    deduplication_key: Mapped[str] = mapped_column(sa.String(256), nullable=False)


class JobModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        sa.Index("ix_jobs_state_updated_at", "state", "updated_at"),
    )

    job_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    file_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("files.file_id", ondelete="RESTRICT"),
        nullable=False,
    )
    watcher_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watchers.watcher_id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_folder_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watcher_sources.source_folder_id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_display_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    source_container_locator: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    source_file_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    source_extension: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    source_size_bytes: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    source_sha256: Mapped[str | None] = mapped_column(sa.String(64))
    detected_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    stable_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    state: Mapped[str] = mapped_column(JOB_STATE, nullable=False)
    terminal_state: Mapped[str | None] = mapped_column(JOB_STATE)
    attempt_number: Mapped[int] = mapped_column(sa.Integer(), nullable=False, default=0)
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)
    latest_error_code: Mapped[str | None] = mapped_column(sa.String(64))


class JobStateHistoryModel(Base, CreatedAtMixin):
    __tablename__ = "job_state_history"
    __table_args__ = (
        sa.Index("ix_job_state_history_job_id_transitioned_at", "job_id", "transitioned_at"),
        sa.UniqueConstraint("job_id", "transition_sequence", name="uq_job_state_history_job_id_transition_sequence"),
        sa.UniqueConstraint("event_id", name="uq_job_state_history_event_id"),
    )

    history_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    previous_state: Mapped[str | None] = mapped_column(JOB_STATE)
    new_state: Mapped[str] = mapped_column(JOB_STATE, nullable=False)
    actor_service: Mapped[str] = mapped_column(ACTOR_SERVICE, nullable=False)
    reason_code: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    transition_sequence: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    event_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))
    transitioned_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)


class ValidationAttemptModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "validation_attempts"
    __table_args__ = (
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_validation_attempts_job_id_attempt_number"),
    )

    validation_attempt_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    validation_status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    rules_applied: Mapped[list[str]] = mapped_column(_string_list_type(), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(_string_list_type(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(sa.Float())
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)


class ProcessingAttemptModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "processing_attempts"
    __table_args__ = (
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_processing_attempts_job_id_attempt_number"),
    )

    processing_attempt_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    engine: Mapped[str] = mapped_column(PROCESSING_ENGINE, nullable=False)
    engine_version: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    input_locator: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    output_locator: Mapped[str | None] = mapped_column(sa.String(1024))
    summary_locator: Mapped[str | None] = mapped_column(sa.String(1024))
    row_count: Mapped[int | None] = mapped_column(sa.BigInteger())
    record_count: Mapped[int | None] = mapped_column(sa.BigInteger())
    byte_count: Mapped[int | None] = mapped_column(sa.BigInteger())
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(sa.Float())
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)


class DeliveryAttemptModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "delivery_attempts"
    __table_args__ = (
        sa.Index("ix_delivery_attempts_status_updated_at", "status", "updated_at"),
        sa.UniqueConstraint(
            "job_id",
            "destination_folder_id",
            "attempt_number",
            name="uq_delivery_attempts_job_id_destination_folder_id_attempt_number",
        ),
    )

    delivery_attempt_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    destination_folder_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watcher_destinations.destination_folder_id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    matched_route_tags: Mapped[list[str]] = mapped_column(_string_list_type(), nullable=False)
    temporary_locator: Mapped[str | None] = mapped_column(sa.String(1024))
    finalized_locator: Mapped[str | None] = mapped_column(sa.String(1024))
    manifest_locator: Mapped[str | None] = mapped_column(sa.String(1024))
    checksum_sha256: Mapped[str | None] = mapped_column(sa.String(64))
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(sa.String(64))
    started_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)


class OutputManifestModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "output_manifests"

    output_manifest_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    watcher_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watchers.watcher_id", ondelete="RESTRICT"),
        nullable=False,
    )
    schema_version: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    manifest_locator: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    processing_summary_locator: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    produced_output_locators: Mapped[list[str]] = mapped_column(_string_list_type(), nullable=False)
    source_sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    output_sha256: Mapped[str | None] = mapped_column(sa.String(64))
    destination_outcomes: Mapped[list[dict[str, Any]]] = mapped_column(_json_payload_type(), nullable=False)
    finalized_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)


class RetryScheduleModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "retry_schedules"
    __table_args__ = (
        sa.Index("ix_retry_schedules_due_at_status", "due_at", "status"),
    )

    retry_schedule_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    failed_stage: Mapped[str] = mapped_column(RETRY_STAGE, nullable=False)
    failure_class: Mapped[str] = mapped_column(FAILURE_CLASS, nullable=False)
    due_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    backoff_seconds: Mapped[float] = mapped_column(sa.Float(), nullable=False)
    attempt_number: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    max_attempts: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    jitter_enabled: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    next_stage: Mapped[str] = mapped_column(RETRY_STAGE, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(sa.String(64))
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)


class EventOutboxModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "event_outbox"
    __table_args__ = (
        sa.Index("ix_event_outbox_status_next_publish_at", "status", "next_publish_at"),
        sa.Index("ix_event_outbox_event_type_occurred_at", "event_type", "occurred_at"),
        sa.UniqueConstraint("event_id", name="uq_event_outbox_event_id"),
    )

    outbox_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    event_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)
    schema_version: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    stream_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    producer: Mapped[str] = mapped_column(ACTOR_SERVICE, nullable=False)
    job_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))
    watcher_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    attempt_number: Mapped[int | None] = mapped_column(sa.Integer())
    occurred_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(_json_payload_type(), nullable=False)
    status: Mapped[str] = mapped_column(OUTBOX_STATUS, nullable=False)
    publish_attempts: Mapped[int] = mapped_column(sa.Integer(), nullable=False, default=0)
    next_publish_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    published_stream_id: Mapped[str | None] = mapped_column(sa.String(128))
    last_error_code: Mapped[str | None] = mapped_column(sa.String(64))


class EventOffsetModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "event_offsets"
    __table_args__ = (
        sa.UniqueConstraint("consumer_group", "stream_name", name="uq_event_offsets_consumer_group_stream_name"),
    )

    event_offset_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    consumer_group: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    stream_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    redis_stream_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    last_processed_event_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))


class IdempotencyKeyModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        sa.UniqueConstraint("scope", "idempotency_key", name="uq_idempotency_keys_scope_idempotency_key"),
    )

    idempotency_key_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    scope: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(sa.String(128))
    target_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    target_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)
    first_response_json: Mapped[dict[str, Any] | None] = mapped_column(_json_payload_type())
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    duplicate_detected_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class StageOwnershipClaimModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "stage_ownership_claims"
    __table_args__ = (
        sa.Index("ix_stage_ownership_claims_stage_claim_status_lease_expires_at", "stage", "claim_status", "lease_expires_at"),
        sa.UniqueConstraint("job_id", "stage", "attempt_number", name="uq_stage_ownership_claims_job_id_stage_attempt_number"),
    )

    claim_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(STAGE_NAME, nullable=False)
    attempt_number: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    owner_service: Mapped[str] = mapped_column(ACTOR_SERVICE, nullable=False)
    lease_expires_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    claim_status: Mapped[str] = mapped_column(CLAIM_STATUS, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    recovered_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    recovered_by_service: Mapped[str | None] = mapped_column(sa.String(64))
    correlation_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))


class DuplicateSuppressionObservationModel(Base, CreatedAtMixin):
    __tablename__ = "duplicate_suppression_observations"
    __table_args__ = (
        sa.Index("ix_duplicate_suppression_observations_existing_job_id_observed_at", "existing_job_id", "observed_at"),
    )

    duplicate_observation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    existing_job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    watcher_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_folder_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watcher_sources.source_folder_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_display_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    byte_size: Mapped[int] = mapped_column(sa.BigInteger(), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(sa.String(64))
    observed_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    reason_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)


class QuarantineRecordModel(Base, CreatedAtMixin, UpdatedAtMixin):
    __tablename__ = "quarantine_records"
    __table_args__ = (
        sa.Index("ix_quarantine_records_job_id", "job_id"),
    )

    quarantine_record_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("jobs.job_id", ondelete="CASCADE"),
        nullable=False,
    )
    file_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("files.file_id", ondelete="CASCADE"),
        nullable=False,
    )
    watcher_id: Mapped[UUID] = mapped_column(
        sa.ForeignKey("watchers.watcher_id", ondelete="RESTRICT"),
        nullable=False,
    )
    validation_attempt_id: Mapped[UUID | None] = mapped_column(
        sa.ForeignKey("validation_attempts.validation_attempt_id", ondelete="SET NULL"),
    )
    schema_version: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    source_display_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    source_sha256: Mapped[str | None] = mapped_column(sa.String(64))
    quarantine_locator: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    quarantine_display_path: Mapped[str | None] = mapped_column(sa.String(1024))
    reason_code: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    copy_status: Mapped[str] = mapped_column(COPY_STATUS, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(sa.String(64))
    operator_message: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)


class OperationalLogSummaryModel(Base, CreatedAtMixin):
    __tablename__ = "operational_log_summaries"
    __table_args__ = (
        sa.Index("ix_operational_log_summaries_created_at", "created_at"),
    )

    log_summary_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    job_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))
    watcher_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))
    event_name: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    error_code: Mapped[str | None] = mapped_column(sa.String(64))
    sanitized_message: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))


class HealthObservationModel(Base, CreatedAtMixin):
    __tablename__ = "health_observations"
    __table_args__ = (
        sa.Index("ix_health_observations_created_at", "created_at"),
    )

    health_observation_id: Mapped[UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True)
    watcher_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))
    folder_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))
    folder_role: Mapped[str | None] = mapped_column(HEALTH_FOLDER_ROLE)
    dependency_name: Mapped[str | None] = mapped_column(sa.String(64))
    status: Mapped[str] = mapped_column(OPERATIONAL_STATUS, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(sa.String(64))
    checked_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[UUID | None] = mapped_column(sa.Uuid(as_uuid=True))


__all__ = [
    "ACTOR_SERVICE",
    "ALL_TABLE_NAMES",
    "CLAIM_STATUS",
    "COPY_STATUS",
    "ControlCommandModel",
    "DeliveryAttemptModel",
    "DuplicateSuppressionObservationModel",
    "EventOffsetModel",
    "EventOutboxModel",
    "FAILURE_CLASS",
    "FileModel",
    "HealthObservationModel",
    "IdempotencyKeyModel",
    "JOB_STATE",
    "JobModel",
    "JobStateHistoryModel",
    "OPERATIONAL_STATUS",
    "OUTBOX_STATUS",
    "OperationalLogSummaryModel",
    "OutputManifestModel",
    "PROCESSING_ENGINE",
    "ProcessingAttemptModel",
    "QuarantineRecordModel",
    "RETRY_STAGE",
    "ROUTE_POLICY",
    "RetryScheduleModel",
    "STAGE_NAME",
    "StageOwnershipClaimModel",
    "TERMINAL_JOB_STATES",
    "ValidationAttemptModel",
    "WATCHER_LIFECYCLE_STATE",
    "WatcherDestinationModel",
    "WatcherModel",
    "WatcherRouteMatchModel",
    "WatcherSourceModel",
]
