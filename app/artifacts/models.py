"""Pydantic models bound to the documented artifact JSON schemas."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import Field, StringConstraints
from typing_extensions import Annotated

from app._schema_types import (
    ErrorCode,
    ExtensibleSchemaModel,
    JsonObject,
    Rfc3339Utc,
    SafeDisplayPath,
    SafeLocator,
    SchemaModel,
    SchemaVersion,
    Sha256Hex,
)


class ProcessingSummary(ExtensibleSchemaModel):
    schema_version: SchemaVersion
    job_id: UUID
    engine: Literal["spark"]
    engine_version: str
    input_locator: Annotated[SafeLocator, StringConstraints(min_length=1)]
    output_locator: Annotated[SafeLocator, StringConstraints(min_length=1)]
    source_sha256: Sha256Hex
    processor_version: str
    row_count: Annotated[int | None, Field(ge=0)] = None
    record_count: Annotated[int | None, Field(ge=0)] = None
    byte_count: Annotated[int | None, Field(ge=0)] = None
    started_at: Rfc3339Utc
    completed_at: Rfc3339Utc
    duration_seconds: Annotated[int, Field(ge=0)]
    status: Literal["processed", "failed"]
    correlation_id: UUID


class OutputManifest(SchemaModel):
    schema_version: SchemaVersion
    job_id: UUID
    watcher_id: UUID
    source_sha256: Sha256Hex
    processor_version: str
    processing_summary_locator: Annotated[SafeLocator, StringConstraints(min_length=1)]
    produced_output_locators: list[Annotated[SafeLocator, StringConstraints(min_length=1)]]
    started_at: Rfc3339Utc
    completed_at: Rfc3339Utc
    duration_seconds: Annotated[int, Field(ge=0)]
    destination_outcomes: list[JsonObject]
    status: Literal["processed", "delivered", "completed_with_delivery_errors", "failed"]
    created_at: Rfc3339Utc
    correlation_id: UUID


class QuarantineRecord(SchemaModel):
    schema_version: SchemaVersion
    job_id: UUID
    watcher_id: UUID
    source_display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1)]
    source_sha256: Sha256Hex
    reason_code: ErrorCode
    operator_message: Annotated[str, StringConstraints(min_length=1)]
    quarantine_locator: Annotated[SafeLocator, StringConstraints(min_length=1)]
    quarantine_display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1)]
    copy_status: Literal["copied", "copy_failed", "not_copied_security_block"]
    created_at: Rfc3339Utc
    correlation_id: UUID


ARTIFACT_MODEL_BY_SCHEMA_NAME = {
    "output_manifest": OutputManifest,
    "processing_summary": ProcessingSummary,
    "quarantine_record": QuarantineRecord,
}


__all__ = [
    "ARTIFACT_MODEL_BY_SCHEMA_NAME",
    "OutputManifest",
    "ProcessingSummary",
    "QuarantineRecord",
]
