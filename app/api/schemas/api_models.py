"""Pydantic models bound to the documented API JSON schemas."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, StringConstraints
from typing_extensions import Annotated

from app._schema_types import (
    AbsoluteContainerPath,
    ErrorCode,
    EventTypeName,
    JsonObject,
    Rfc3339Utc,
    RouteTag,
    SafeDisplayPath,
    SchemaModel,
    SchemaVersion,
    SectionId,
    ServiceVersion,
    Sha256Hex,
)
from app.api.errors import StandardError as RuntimeStandardError
from app.config.path_policy import PathValidationResult

HealthColor = Literal["green", "yellow", "red"]
ReadinessState = Literal["ready", "not_ready"]
RoutePolicy = Literal["tag_match_all_destinations"]
WatcherLifecycleState = Literal["CREATED", "ACTIVE", "PAUSED", "STOPPING", "STOPPED", "ERROR"]
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
DependencyName = Literal["postgres", "redis_streams", "spark", "filesystem_roots"]
DependencyStatus = Literal["ready", "degraded", "unavailable"]
CommandResourceType = Literal["watcher", "job"]
CommandStatus = Literal["accepted", "running", "succeeded", "failed", "expired"]
DeliveryDestinationStatus = Literal["pending", "delivered", "failed", "skipped"]
OperationalLogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
ThemeName = Literal["default_light", "high_contrast"]
LayoutProfile = Literal["operator_default", "reviewer_demo"]

Name128 = Annotated[str, StringConstraints(min_length=1, max_length=128)]
Text256 = Annotated[str, StringConstraints(min_length=1, max_length=256)]
NullableText256 = Annotated[str | None, StringConstraints(max_length=256)]
NullableText64 = Annotated[str | None, StringConstraints(max_length=64)]
NullableText512 = Annotated[str | None, StringConstraints(max_length=512)]
ColorToken = Annotated[str, StringConstraints(pattern=r"^#?[A-Za-z0-9(),. %_-]+$")]


class StandardError(SchemaModel):
    error_code: ErrorCode
    message: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    field: NullableText256
    resource_id: UUID | None
    current_state: NullableText64
    correlation_id: UUID

    @classmethod
    def from_standard_error(cls, error: RuntimeStandardError) -> "StandardError":
        return cls(**error.to_dict())

    def to_standard_error(self) -> RuntimeStandardError:
        return RuntimeStandardError(**self.model_dump(mode="json"))


class HealthResponse(SchemaModel):
    status: ReadinessState
    service: Literal["stream_lite_api"]
    version: ServiceVersion
    checked_at: Rfc3339Utc
    correlation_id: UUID


class DependencyHealthItem(SchemaModel):
    name: DependencyName
    status: DependencyStatus
    checked_at: Rfc3339Utc
    message: NullableText256
    error_code: NullableText64 = None


class DependencyHealthResponse(SchemaModel):
    status: ReadinessState
    dependencies: Annotated[list[DependencyHealthItem], Field(min_length=4)]
    checked_at: Rfc3339Utc
    correlation_id: UUID


class RouteTaggedFolderSpec(SchemaModel):
    folder_id: UUID
    display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1, max_length=1024)]
    route_tags: Annotated[list[RouteTag], Field(min_length=1)]
    route_tags_text: Text256
    health_status: HealthColor | None = None
    reason_code: NullableText64 = None


class WatcherCreateRequest(SchemaModel):
    name: Name128
    sources: Annotated[list[RouteTaggedFolderSpec], Field(min_length=1)]
    destinations: Annotated[list[RouteTaggedFolderSpec], Field(min_length=1)]
    route_policy: RoutePolicy
    enabled: bool = False
    correlation_id: UUID | None = None


class WatcherPatchRequest(SchemaModel):
    name: Name128 | None = None
    sources: Annotated[list[RouteTaggedFolderSpec], Field(min_length=1)] | None = None
    destinations: Annotated[list[RouteTaggedFolderSpec], Field(min_length=1)] | None = None
    route_policy: RoutePolicy | None = None
    enabled: bool | None = None
    correlation_id: UUID | None = None


class LifecycleCommandRequest(SchemaModel):
    requested_by: Name128
    reason: NullableText512 = None
    correlation_id: UUID | None = None


class RetryCommandRequest(SchemaModel):
    requested_by: Name128
    reason: NullableText512 = None
    correlation_id: UUID | None = None


class RoutePreviewRequest(SchemaModel):
    sources: Annotated[list[RouteTaggedFolderSpec], Field(min_length=1)]
    destinations: Annotated[list[RouteTaggedFolderSpec], Field(min_length=1)]
    route_policy: RoutePolicy
    correlation_id: UUID | None = None


class RoutePreviewMatch(SchemaModel):
    source_folder_id: UUID
    matched_destination_ids: list[UUID]


class RoutePreviewResponse(SchemaModel):
    route_policy: RoutePolicy
    source_matches: list[RoutePreviewMatch]
    unmatched_sources: list[UUID]
    unmatched_destinations: list[UUID]
    status: HealthColor
    correlation_id: UUID


class WatcherRoutePreviewSummary(SchemaModel):
    status: HealthColor
    matched_destination_count: Annotated[int, Field(ge=0)]
    unmatched_source_count: Annotated[int, Field(ge=0)]
    unmatched_destination_count: Annotated[int, Field(ge=0)]
    generated_at: Rfc3339Utc


class WatcherDetailResponse(SchemaModel):
    watcher_id: UUID
    name: Name128
    lifecycle_state: WatcherLifecycleState
    operational_status: HealthColor
    sources: list[RouteTaggedFolderSpec]
    destinations: list[RouteTaggedFolderSpec]
    route_policy: RoutePolicy
    route_preview: WatcherRoutePreviewSummary
    created_at: Rfc3339Utc
    updated_at: Rfc3339Utc
    correlation_id: UUID


class WatcherListItem(SchemaModel):
    watcher_id: UUID
    name: Name128
    lifecycle_state: WatcherLifecycleState
    operational_status: HealthColor
    source_count: Annotated[int, Field(ge=0)]
    destination_count: Annotated[int, Field(ge=0)]
    updated_at: Rfc3339Utc


class WatcherListResponse(SchemaModel):
    items: list[WatcherListItem]
    limit: Annotated[int, Field(ge=1, le=500)]
    offset: Annotated[int, Field(ge=0)]
    total: Annotated[int, Field(ge=0)]
    correlation_id: UUID


class JobDestinationSummary(SchemaModel):
    destination_folder_id: UUID
    display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1, max_length=1024)]
    route_tags: list[RouteTag]
    matched_tags: list[RouteTag]
    status: DeliveryDestinationStatus
    reason_code: NullableText64


class JobAttemptSummary(SchemaModel):
    validation_attempts: Annotated[int, Field(ge=0)]
    processing_attempts: Annotated[int, Field(ge=0)]
    delivery_attempts: Annotated[int, Field(ge=0)]
    retry_attempts: Annotated[int, Field(ge=0)]
    last_attempt_at: Rfc3339Utc | None


class JobSource(SchemaModel):
    file_id: UUID
    display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1, max_length=1024)]
    source_folder_id: UUID
    size_bytes: Annotated[int, Field(ge=0)]
    sha256: Sha256Hex


class JobDetailResponse(SchemaModel):
    job_id: UUID
    watcher_id: UUID
    state: JobState
    source: JobSource
    destinations: list[JobDestinationSummary]
    attempt_summary: JobAttemptSummary
    latest_error: StandardError | None
    created_at: Rfc3339Utc
    updated_at: Rfc3339Utc
    correlation_id: UUID


class JobListItem(SchemaModel):
    job_id: UUID
    watcher_id: UUID
    state: JobState
    source_display_path: Annotated[
        SafeDisplayPath,
        StringConstraints(min_length=1, max_length=1024),
    ]
    created_at: Rfc3339Utc
    updated_at: Rfc3339Utc
    latest_error_code: NullableText64


class JobListResponse(SchemaModel):
    items: list[JobListItem]
    limit: Annotated[int, Field(ge=1, le=500)]
    offset: Annotated[int, Field(ge=0)]
    total: Annotated[int, Field(ge=0)]
    correlation_id: UUID


class JobHistoryEntry(SchemaModel):
    from_state: JobState | None
    to_state: JobState
    actor_service: ActorService
    reason_code: NullableText64
    occurred_at: Rfc3339Utc
    event_id: UUID


class JobHistoryResponse(SchemaModel):
    job_id: UUID
    history: list[JobHistoryEntry]
    correlation_id: UUID


class CommandAcceptedResponse(SchemaModel):
    command_id: UUID
    status: Literal["accepted"]
    target_resource_type: CommandResourceType
    target_resource_id: UUID
    accepted_at: Rfc3339Utc
    correlation_id: UUID


class CommandStatusResponse(SchemaModel):
    command_id: UUID
    status: CommandStatus
    target_resource_type: CommandResourceType
    target_resource_id: UUID
    result: JsonObject | None
    error: StandardError | None
    created_at: Rfc3339Utc
    updated_at: Rfc3339Utc
    correlation_id: UUID


class EventListItem(SchemaModel):
    event_id: UUID
    event_type: EventTypeName
    schema_version: SchemaVersion
    job_id: UUID | None
    watcher_id: UUID | None
    producer: ActorService
    occurred_at: Rfc3339Utc
    stream_name: Literal["stream_lite.lifecycle"]
    correlation_id: UUID


class EventListResponse(SchemaModel):
    items: list[EventListItem]
    limit: Annotated[int, Field(ge=1, le=500)]
    offset: Annotated[int, Field(ge=0)]
    total: Annotated[int, Field(ge=0)]
    correlation_id: UUID


class MetricsSummaryResponse(SchemaModel):
    job_counts: dict[str, Annotated[int, Field(ge=0)]]
    stage_durations_seconds: dict[str, Annotated[float, Field(ge=0)]]
    queue_lag: dict[str, Annotated[int, Field(ge=0)]]
    retry_counts: dict[str, Annotated[int, Field(ge=0)]]
    delivery_counts: dict[str, Annotated[int, Field(ge=0)]]
    watcher_counts: dict[str, Annotated[int, Field(ge=0)]]
    correlation_id: UUID


class OperationalLogItem(SchemaModel):
    timestamp: Rfc3339Utc
    level: OperationalLogLevel
    service: ActorService
    component: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    event: Annotated[str, StringConstraints(min_length=1, max_length=128)]
    correlation_id: UUID | None
    job_id: UUID | None
    file_id: UUID | None
    message: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    error_code: NullableText64
    duration_ms: Annotated[int | None, Field(ge=0)]


class OperationalLogListResponse(SchemaModel):
    items: list[OperationalLogItem]
    limit: Annotated[int, Field(ge=1, le=500)]
    offset: Annotated[int, Field(ge=0)]
    total: Annotated[int, Field(ge=0)]
    correlation_id: UUID


class FolderBrowseItem(SchemaModel):
    name: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1, max_length=1024)]
    is_directory: bool
    is_selectable: bool
    reason_code: NullableText64


class FolderBrowseResponse(SchemaModel):
    purpose: Literal["source", "destination"]
    root: Annotated[SafeDisplayPath, StringConstraints(min_length=1, max_length=1024)]
    items: list[FolderBrowseItem]
    correlation_id: UUID


class PathValidationRequest(SchemaModel):
    purpose: Literal["source", "destination"]
    path: Annotated[AbsoluteContainerPath, StringConstraints(min_length=1, max_length=2048)]
    correlation_id: UUID | None = None


class PathValidationResponse(SchemaModel):
    purpose: Literal["source", "destination"]
    path: Annotated[AbsoluteContainerPath, StringConstraints(min_length=1, max_length=2048)]
    normalized_path: Annotated[
        AbsoluteContainerPath,
        StringConstraints(min_length=1, max_length=2048),
    ]
    display_path: Annotated[SafeDisplayPath, StringConstraints(min_length=1, max_length=1024)]
    status: HealthColor
    reason_code: NullableText64
    message: Annotated[str, StringConstraints(min_length=1, max_length=512)]
    correlation_id: UUID

    @classmethod
    def from_result(cls, result: PathValidationResult) -> "PathValidationResponse":
        return cls(**result.to_dict())


class DashboardLayoutSection(SchemaModel):
    section_id: SectionId
    visible: bool
    order: Annotated[int, Field(ge=0)]


class DashboardPresentationResponse(SchemaModel):
    schema_version: SchemaVersion
    theme_name: ThemeName
    color_tokens: dict[str, ColorToken]
    status_dot_tokens: dict[str, ColorToken]
    layout_profile: LayoutProfile
    layout_sections: list[DashboardLayoutSection]
    refresh_interval_seconds: Annotated[int, Field(ge=1, le=300)]
    correlation_id: UUID


API_MODEL_BY_SCHEMA_NAME = {
    "command_accepted_response": CommandAcceptedResponse,
    "command_status_response": CommandStatusResponse,
    "dashboard_presentation_response": DashboardPresentationResponse,
    "dependency_health_response": DependencyHealthResponse,
    "event_list_response": EventListResponse,
    "folder_browse_response": FolderBrowseResponse,
    "health_response": HealthResponse,
    "job_detail_response": JobDetailResponse,
    "job_history_response": JobHistoryResponse,
    "job_list_response": JobListResponse,
    "lifecycle_command_request": LifecycleCommandRequest,
    "metrics_summary_response": MetricsSummaryResponse,
    "operational_log_list_response": OperationalLogListResponse,
    "path_validation_request": PathValidationRequest,
    "path_validation_response": PathValidationResponse,
    "retry_command_request": RetryCommandRequest,
    "route_preview_request": RoutePreviewRequest,
    "route_preview_response": RoutePreviewResponse,
    "standard_error": StandardError,
    "watcher_create_request": WatcherCreateRequest,
    "watcher_detail_response": WatcherDetailResponse,
    "watcher_list_response": WatcherListResponse,
    "watcher_patch_request": WatcherPatchRequest,
}


__all__ = [
    "API_MODEL_BY_SCHEMA_NAME",
    "CommandAcceptedResponse",
    "CommandStatusResponse",
    "DashboardPresentationResponse",
    "DependencyHealthResponse",
    "EventListResponse",
    "FolderBrowseResponse",
    "HealthResponse",
    "JobDetailResponse",
    "JobHistoryResponse",
    "JobListResponse",
    "LifecycleCommandRequest",
    "MetricsSummaryResponse",
    "OperationalLogListResponse",
    "PathValidationRequest",
    "PathValidationResponse",
    "RetryCommandRequest",
    "RoutePreviewRequest",
    "RoutePreviewResponse",
    "StandardError",
    "WatcherCreateRequest",
    "WatcherDetailResponse",
    "WatcherListResponse",
    "WatcherPatchRequest",
]
