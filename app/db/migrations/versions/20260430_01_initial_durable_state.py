"""Initial durable-state schema for WP-03.

This migration implements the documented v0.1 durable tables with an explicit
downgrade path. Primary application identifiers remain application-owned UUIDs.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260430_01"
down_revision = None
branch_labels = None
depends_on = None


def _json_payload_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def _string_list_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.ARRAY(sa.Text()), "postgresql")


def _enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


watcher_lifecycle_state = _enum(
    "watcher_lifecycle_state",
    "CREATED",
    "ACTIVE",
    "PAUSED",
    "STOPPING",
    "STOPPED",
    "ERROR",
)
operational_status = _enum("operational_status", "green", "yellow", "red")
route_policy = _enum("route_policy", "tag_match_all_destinations")
JOB_STATE_VALUES = (
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
)

# SQLAlchemy renders non-native Enum values as CHECK constraints. PostgreSQL
# requires constraint names to be unique within a table, so columns that reuse
# the same value set in one table need distinct constraint names.
job_state = _enum("job_state", *JOB_STATE_VALUES)
terminal_job_state = _enum("terminal_job_state", *JOB_STATE_VALUES)
previous_job_state = _enum("previous_job_state", *JOB_STATE_VALUES)
new_job_state = _enum("new_job_state", *JOB_STATE_VALUES)
actor_service = _enum(
    "actor_service",
    "api",
    "watcher",
    "validator",
    "processor",
    "delivery",
    "retry_scheduler",
    "event_dispatcher",
    "streamlit",
)
failure_class = _enum("failure_class", "retryable", "non_retryable")
RETRY_STAGE_VALUES = ("validation", "processing", "delivery")
retry_stage = _enum("retry_stage", *RETRY_STAGE_VALUES)
next_retry_stage = _enum("next_retry_stage", *RETRY_STAGE_VALUES)
stage_name = _enum("stage_name", "validation", "processing", "delivery", "retry", "outbox")
command_status = _enum("command_status", "accepted", "running", "succeeded", "failed", "expired")
outbox_status = _enum("outbox_status", "pending", "published", "publish_failed", "dead_lettered")
copy_status = _enum("copy_status", "copied", "copy_failed", "not_copied_security_block")
claim_status = _enum("claim_status", "active", "released", "expired")
health_folder_role = _enum("health_folder_role", "source", "destination")
processing_engine = _enum("processing_engine", "spark")


def upgrade() -> None:
    op.create_table(
        "watchers",
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("lifecycle_state", watcher_lifecycle_state, nullable=False),
        sa.Column("operational_status", operational_status, nullable=False),
        sa.Column("route_policy", route_policy, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("latest_route_preview_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_watchers_name"),
    )
    op.create_index(
        "ix_watchers_lifecycle_state_operational_status",
        "watchers",
        ["lifecycle_state", "operational_status"],
    )

    op.create_table(
        "watcher_sources",
        sa.Column("source_folder_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_path", sa.String(length=1024), nullable=False),
        sa.Column("normalized_path", sa.String(length=1024), nullable=False),
        sa.Column("route_tags", _string_list_type(), nullable=False),
        sa.Column("route_tags_text", sa.Text(), nullable=False),
        sa.Column("health_status", operational_status, nullable=False),
        sa.Column("reason_code", sa.String(length=64)),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("watcher_id", "normalized_path", name="uq_watcher_sources_watcher_id_normalized_path"),
    )
    op.create_index("ix_watcher_sources_watcher_id", "watcher_sources", ["watcher_id"])

    op.create_table(
        "watcher_destinations",
        sa.Column("destination_folder_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_path", sa.String(length=1024), nullable=False),
        sa.Column("normalized_path", sa.String(length=1024), nullable=False),
        sa.Column("route_tags", _string_list_type(), nullable=False),
        sa.Column("route_tags_text", sa.Text(), nullable=False),
        sa.Column("health_status", operational_status, nullable=False),
        sa.Column("reason_code", sa.String(length=64)),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("watcher_id", "normalized_path", name="uq_watcher_destinations_watcher_id_normalized_path"),
    )
    op.create_index("ix_watcher_destinations_watcher_id", "watcher_destinations", ["watcher_id"])

    op.create_table(
        "watcher_route_matches",
        sa.Column("route_match_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_folder_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watcher_sources.source_folder_id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination_folder_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watcher_destinations.destination_folder_id", ondelete="CASCADE")),
        sa.Column("route_policy", route_policy, nullable=False),
        sa.Column("matched_route_tags", _string_list_type(), nullable=False),
        sa.Column("unmatched_reason_code", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_watcher_route_matches_watcher_id", "watcher_route_matches", ["watcher_id"])

    op.create_table(
        "control_commands",
        sa.Column("command_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("target_resource_type", sa.String(length=64), nullable=False),
        sa.Column("target_resource_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("requested_by", sa.String(length=128), nullable=False),
        sa.Column("operator_reason", sa.String(length=512), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("status", command_status, nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("result_locator", sa.String(length=1024)),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "files",
        sa.Column("file_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_folder_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watcher_sources.source_folder_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_display_path", sa.String(length=1024), nullable=False),
        sa.Column("source_container_locator", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_extension", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stable_at", sa.DateTime(timezone=True)),
        sa.Column("deduplication_key", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("deduplication_key", name="uq_files_deduplication_key"),
    )
    op.create_index("ix_files_watcher_id_source_folder_id", "files", ["watcher_id", "source_folder_id"])

    op.create_table(
        "jobs",
        sa.Column("job_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("file_id", sa.Uuid(as_uuid=True), sa.ForeignKey("files.file_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watchers.watcher_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_folder_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watcher_sources.source_folder_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_display_path", sa.String(length=1024), nullable=False),
        sa.Column("source_container_locator", sa.String(length=1024), nullable=False),
        sa.Column("source_file_name", sa.String(length=255), nullable=False),
        sa.Column("source_extension", sa.String(length=32), nullable=False),
        sa.Column("source_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("source_sha256", sa.String(length=64)),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stable_at", sa.DateTime(timezone=True)),
        sa.Column("state", job_state, nullable=False),
        sa.Column("terminal_state", terminal_job_state),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("latest_error_code", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_state_updated_at", "jobs", ["state", "updated_at"])

    op.create_table(
        "job_state_history",
        sa.Column("history_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_state", previous_job_state),
        sa.Column("new_state", new_job_state, nullable=False),
        sa.Column("actor_service", actor_service, nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("transition_sequence", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True)),
        sa.Column("transitioned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "transition_sequence", name="uq_job_state_history_job_id_transition_sequence"),
        sa.UniqueConstraint("event_id", name="uq_job_state_history_event_id"),
    )
    op.create_index("ix_job_state_history_job_id_transitioned_at", "job_state_history", ["job_id", "transitioned_at"])

    op.create_table(
        "validation_attempts",
        sa.Column("validation_attempt_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column("rules_applied", _string_list_type(), nullable=False),
        sa.Column("reason_codes", _string_list_type(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_validation_attempts_job_id_attempt_number"),
    )

    op.create_table(
        "processing_attempts",
        sa.Column("processing_attempt_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("engine", processing_engine, nullable=False),
        sa.Column("engine_version", sa.String(length=64), nullable=False),
        sa.Column("input_locator", sa.String(length=1024), nullable=False),
        sa.Column("output_locator", sa.String(length=1024)),
        sa.Column("summary_locator", sa.String(length=1024)),
        sa.Column("row_count", sa.BigInteger()),
        sa.Column("record_count", sa.BigInteger()),
        sa.Column("byte_count", sa.BigInteger()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "attempt_number", name="uq_processing_attempts_job_id_attempt_number"),
    )

    op.create_table(
        "delivery_attempts",
        sa.Column("delivery_attempt_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("destination_folder_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watcher_destinations.destination_folder_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("matched_route_tags", _string_list_type(), nullable=False),
        sa.Column("temporary_locator", sa.String(length=1024)),
        sa.Column("finalized_locator", sa.String(length=1024)),
        sa.Column("manifest_locator", sa.String(length=1024)),
        sa.Column("checksum_sha256", sa.String(length=64)),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failure_code", sa.String(length=64)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "job_id",
            "destination_folder_id",
            "attempt_number",
            name="uq_delivery_attempts_job_dest_attempt",
        ),
    )
    op.create_index("ix_delivery_attempts_status_updated_at", "delivery_attempts", ["status", "updated_at"])

    op.create_table(
        "output_manifests",
        sa.Column("output_manifest_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watchers.watcher_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("manifest_locator", sa.String(length=1024), nullable=False),
        sa.Column("processing_summary_locator", sa.String(length=1024), nullable=False),
        sa.Column("produced_output_locators", _string_list_type(), nullable=False),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("output_sha256", sa.String(length=64)),
        sa.Column("destination_outcomes", _json_payload_type(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "retry_schedules",
        sa.Column("retry_schedule_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("failed_stage", retry_stage, nullable=False),
        sa.Column("failure_class", failure_class, nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("backoff_seconds", sa.Float(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("jitter_enabled", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("next_stage", next_retry_stage, nullable=False),
        sa.Column("last_error_code", sa.String(length=64)),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retry_schedules_due_at_status", "retry_schedules", ["due_at", "status"])

    op.create_table(
        "event_outbox",
        sa.Column("outbox_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("event_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("stream_name", sa.String(length=128), nullable=False),
        sa.Column("producer", actor_service, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True)),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True)),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("attempt_number", sa.Integer()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", _json_payload_type(), nullable=False),
        sa.Column("status", outbox_status, nullable=False),
        sa.Column("publish_attempts", sa.Integer(), nullable=False),
        sa.Column("next_publish_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("published_stream_id", sa.String(length=128)),
        sa.Column("last_error_code", sa.String(length=64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_event_outbox_event_id"),
    )
    op.create_index("ix_event_outbox_status_next_publish_at", "event_outbox", ["status", "next_publish_at"])
    op.create_index("ix_event_outbox_event_type_occurred_at", "event_outbox", ["event_type", "occurred_at"])

    op.create_table(
        "event_offsets",
        sa.Column("event_offset_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("consumer_group", sa.String(length=128), nullable=False),
        sa.Column("stream_name", sa.String(length=128), nullable=False),
        sa.Column("redis_stream_id", sa.String(length=128), nullable=False),
        sa.Column("last_processed_event_id", sa.Uuid(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("consumer_group", "stream_name", name="uq_event_offsets_consumer_group_stream_name"),
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("idempotency_key_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=False),
        sa.Column("payload_hash", sa.String(length=128)),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("first_response_json", _json_payload_type()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("duplicate_detected_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scope", "idempotency_key", name="uq_idempotency_keys_scope_idempotency_key"),
    )

    op.create_table(
        "stage_ownership_claims",
        sa.Column("claim_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", stage_name, nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("owner_service", actor_service, nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claim_status", claim_status, nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True)),
        sa.Column("recovered_at", sa.DateTime(timezone=True)),
        sa.Column("recovered_by_service", sa.String(length=64)),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "stage", "attempt_number", name="uq_stage_ownership_claims_job_id_stage_attempt_number"),
    )
    op.create_index(
        "ix_stage_ownership_claims_stage_claim_status_lease_expires_at",
        "stage_ownership_claims",
        ["stage", "claim_status", "lease_expires_at"],
    )

    op.create_table(
        "duplicate_suppression_observations",
        sa.Column("duplicate_observation_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("existing_job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watchers.watcher_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_folder_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watcher_sources.source_folder_id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_display_path", sa.String(length=1024), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("content_hash", sa.String(length=64)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_dup_obs_existing_job_observed_at",
        "duplicate_suppression_observations",
        ["existing_job_id", "observed_at"],
    )

    op.create_table(
        "quarantine_records",
        sa.Column("quarantine_record_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True), sa.ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", sa.Uuid(as_uuid=True), sa.ForeignKey("files.file_id", ondelete="CASCADE"), nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True), sa.ForeignKey("watchers.watcher_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("validation_attempt_id", sa.Uuid(as_uuid=True), sa.ForeignKey("validation_attempts.validation_attempt_id", ondelete="SET NULL")),
        sa.Column("schema_version", sa.String(length=16), nullable=False),
        sa.Column("source_display_path", sa.String(length=1024), nullable=False),
        sa.Column("source_sha256", sa.String(length=64)),
        sa.Column("quarantine_locator", sa.String(length=1024), nullable=False),
        sa.Column("quarantine_display_path", sa.String(length=1024)),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("copy_status", copy_status, nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64)),
        sa.Column("operator_message", sa.String(length=512), nullable=False),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_quarantine_records_job_id", "quarantine_records", ["job_id"])

    op.create_table(
        "operational_log_summaries",
        sa.Column("log_summary_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("job_id", sa.Uuid(as_uuid=True)),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True)),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("error_code", sa.String(length=64)),
        sa.Column("sanitized_message", sa.String(length=512), nullable=False),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operational_log_summaries_created_at", "operational_log_summaries", ["created_at"])

    op.create_table(
        "health_observations",
        sa.Column("health_observation_id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("watcher_id", sa.Uuid(as_uuid=True)),
        sa.Column("folder_id", sa.Uuid(as_uuid=True)),
        sa.Column("folder_role", health_folder_role),
        sa.Column("dependency_name", sa.String(length=64)),
        sa.Column("status", operational_status, nullable=False),
        sa.Column("reason_code", sa.String(length=64)),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.Uuid(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_health_observations_created_at", "health_observations", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_health_observations_created_at", table_name="health_observations")
    op.drop_table("health_observations")
    op.drop_index("ix_operational_log_summaries_created_at", table_name="operational_log_summaries")
    op.drop_table("operational_log_summaries")
    op.drop_index("ix_quarantine_records_job_id", table_name="quarantine_records")
    op.drop_table("quarantine_records")
    op.drop_index(
        "ix_dup_obs_existing_job_observed_at",
        table_name="duplicate_suppression_observations",
    )
    op.drop_table("duplicate_suppression_observations")
    op.drop_index(
        "ix_stage_ownership_claims_stage_claim_status_lease_expires_at",
        table_name="stage_ownership_claims",
    )
    op.drop_table("stage_ownership_claims")
    op.drop_table("idempotency_keys")
    op.drop_table("event_offsets")
    op.drop_index("ix_event_outbox_event_type_occurred_at", table_name="event_outbox")
    op.drop_index("ix_event_outbox_status_next_publish_at", table_name="event_outbox")
    op.drop_table("event_outbox")
    op.drop_index("ix_retry_schedules_due_at_status", table_name="retry_schedules")
    op.drop_table("retry_schedules")
    op.drop_table("output_manifests")
    op.drop_index("ix_delivery_attempts_status_updated_at", table_name="delivery_attempts")
    op.drop_table("delivery_attempts")
    op.drop_table("processing_attempts")
    op.drop_table("validation_attempts")
    op.drop_index("ix_job_state_history_job_id_transitioned_at", table_name="job_state_history")
    op.drop_table("job_state_history")
    op.drop_index("ix_jobs_state_updated_at", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_files_watcher_id_source_folder_id", table_name="files")
    op.drop_table("files")
    op.drop_table("control_commands")
    op.drop_index("ix_watcher_route_matches_watcher_id", table_name="watcher_route_matches")
    op.drop_table("watcher_route_matches")
    op.drop_index("ix_watcher_destinations_watcher_id", table_name="watcher_destinations")
    op.drop_table("watcher_destinations")
    op.drop_index("ix_watcher_sources_watcher_id", table_name="watcher_sources")
    op.drop_table("watcher_sources")
    op.drop_index("ix_watchers_lifecycle_state_operational_status", table_name="watchers")
    op.drop_table("watchers")
