# API Schema Contract Inventory

Schemas are implementation contracts for FastAPI request/response models. JSON schema files live under `stream_lite/schemas/api/`. Valid and invalid example payloads live under `stream_lite/schemas/examples/api/`.

## Shared Field Types

| Type | Contract |
|---|---|
| `uuid` | RFC 4122 UUID string; lowercase canonical serialization preferred. |
| `rfc3339_utc` | RFC 3339 UTC string ending in `Z`. |
| `display_path` | Sanitized path relative to configured mount or approved container mount; never host-only absolute path. |
| `correlation_id` | UUID created at API boundary when caller does not provide one. |
| `route_tag` | Uppercase string matching `^[A-Z0-9_-]{1,32}$`. |
| `job_state` | One of the states documented in `REQ-006`. |
| `duration_seconds` | Numeric seconds for API metric summaries and Prometheus duration histograms. Structured logs may retain `duration_ms` for log-event readability only. |

## Request Schemas

| Schema | File | Required fields | Optional fields | Validation | Example |
|---|---|---|---|---|---|
| `WatcherCreateRequest` | `schemas/api/watcher_create_request.schema.json` | `name`, `sources`, `destinations`, `route_policy` | `enabled`, `correlation_id` | At least one source and one destination; tags valid; paths allowlisted. | `schemas/examples/api/watcher_create_request.valid.json` |
| `WatcherPatchRequest` | `schemas/api/watcher_patch_request.schema.json` | none | `name`, `sources`, `destinations`, `route_policy`, `enabled`, `correlation_id` | Only allowed while watcher not actively processing new detection. | `schemas/examples/api/watcher_patch_request.valid.json` |
| `LifecycleCommandRequest` | `schemas/api/lifecycle_command_request.schema.json` | `requested_by` | `reason`, `correlation_id` | `requested_by` max 128 chars; no executable content. | `schemas/examples/api/lifecycle_command_request.valid.json` |
| `RoutePreviewRequest` | `schemas/api/route_preview_request.schema.json` | `sources`, `destinations`, `route_policy` | `correlation_id` | Same tag/path rules as watcher create. | `schemas/examples/api/route_preview_request.valid.json` |
| `RetryCommandRequest` | `schemas/api/retry_command_request.schema.json` | `requested_by` | `reason`, `correlation_id` | Job must be retry eligible. | `schemas/examples/api/retry_command_request.valid.json` |
| `PathValidationRequest` | `schemas/api/path_validation_request.schema.json` | `purpose`, `path` | `correlation_id` | `purpose` is `source` or `destination`; path normalized and allowlisted. | `schemas/examples/api/path_validation_request.valid.json` |

## Response Schemas

| Schema | File | Required fields | Notes | Example |
|---|---|---|---|---|
| `HealthResponse` | `schemas/api/health_response.schema.json` | `status`, `service`, `version`, `correlation_id`, `checked_at` | `status` is `ready` or `not_ready`. | `schemas/examples/api/health_response.valid.json` |
| `DependencyHealthResponse` | `schemas/api/dependency_health_response.schema.json` | `status`, `dependencies`, `correlation_id`, `checked_at` | Dependencies include `postgres`, `redis_streams`, `spark`, `filesystem_roots`. | `schemas/examples/api/dependency_health_response.valid.json` |
| `WatcherDetailResponse` | `schemas/api/watcher_detail_response.schema.json` | `watcher_id`, `name`, `lifecycle_state`, `operational_status`, `sources`, `destinations`, `route_policy`, `route_preview`, `created_at`, `updated_at`, `correlation_id` | Includes normalized and original tag text. | `schemas/examples/api/watcher_detail_response.valid.json` |
| `WatcherListResponse` | `schemas/api/watcher_list_response.schema.json` | `items`, `limit`, `offset`, `total`, `correlation_id` | Items use compact watcher summary. | `schemas/examples/api/watcher_list_response.valid.json` |
| `RoutePreviewResponse` | `schemas/api/route_preview_response.schema.json` | `route_policy`, `source_matches`, `unmatched_sources`, `unmatched_destinations`, `status`, `correlation_id` | `status` is `green`, `yellow`, or `red`. | `schemas/examples/api/route_preview_response.valid.json` |
| `JobDetailResponse` | `schemas/api/job_detail_response.schema.json` | `job_id`, `watcher_id`, `state`, `source`, `destinations`, `attempt_summary`, `latest_error`, `created_at`, `updated_at`, `correlation_id` | Does not expose host-only paths. | `schemas/examples/api/job_detail_response.valid.json` |
| `JobListResponse` | `schemas/api/job_list_response.schema.json` | `items`, `limit`, `offset`, `total`, `correlation_id` | Supports filters from REQ-010. | `schemas/examples/api/job_list_response.valid.json` |
| `JobHistoryResponse` | `schemas/api/job_history_response.schema.json` | `job_id`, `history`, `correlation_id` | History rows ordered by transition time ascending. | `schemas/examples/api/job_history_response.valid.json` |
| `CommandAcceptedResponse` | `schemas/api/command_accepted_response.schema.json` | `command_id`, `status`, `target_resource_type`, `target_resource_id`, `accepted_at`, `correlation_id` | Initial status is `accepted`. | `schemas/examples/api/command_accepted_response.valid.json` |
| `CommandStatusResponse` | `schemas/api/command_status_response.schema.json` | `command_id`, `status`, `target_resource_type`, `target_resource_id`, `result`, `error`, `created_at`, `updated_at`, `correlation_id` | Terminal statuses: `succeeded`, `failed`, `expired`. | `schemas/examples/api/command_status_response.valid.json` |
| `EventListResponse` | `schemas/api/event_list_response.schema.json` | `items`, `limit`, `offset`, `total`, `correlation_id` | Items derive from outbox and consumed offsets. | `schemas/examples/api/event_list_response.valid.json` |
| `MetricsSummaryResponse` | `schemas/api/metrics_summary_response.schema.json` | `job_counts`, `stage_durations_seconds`, `queue_lag`, `retry_counts`, `delivery_counts`, `watcher_counts`, `correlation_id` | Used by dashboard summary cards; duration metrics are seconds. | `schemas/examples/api/metrics_summary_response.valid.json` |
| `OperationalLogListResponse` | `schemas/api/operational_log_list_response.schema.json` | `items`, `limit`, `offset`, `total`, `correlation_id` | Backed by persisted operational log summary. | `schemas/examples/api/operational_log_list_response.valid.json` |
| `FolderBrowseResponse` | `schemas/api/folder_browse_response.schema.json` | `purpose`, `root`, `items`, `correlation_id` | Items are allowlisted candidate folders only. | `schemas/examples/api/folder_browse_response.valid.json` |
| `PathValidationResponse` | `schemas/api/path_validation_response.schema.json` | `purpose`, `path`, `normalized_path`, `display_path`, `status`, `reason_code`, `message`, `correlation_id` | Never returns host-only absolute paths. | `schemas/examples/api/path_validation_response.valid.json` |
| `StandardError` | `schemas/api/standard_error.schema.json` | `error_code`, `message`, `field`, `resource_id`, `current_state`, `correlation_id` | Shared sanitized error envelope used by failed command status and API error examples. | `schemas/examples/api/standard_error.valid.json` |
| `DashboardPresentationResponse` | `schemas/api/dashboard_presentation_response.schema.json` | `schema_version`, `theme_name`, `color_tokens`, `status_dot_tokens`, `layout_profile`, `layout_sections`, `refresh_interval_seconds`, `correlation_id` | Read-only v0.1. | `schemas/examples/api/dashboard_presentation_response.valid.json` |

## Example Fixture Rule

Each API schema shall have at least one `*.valid.json` fixture under `schemas/examples/api/`. Every active API schema shall also include one `*.invalid.json` fixture before implementation tests are generated; additional enum, timestamp, and path-safety invalid fixtures may be added later.

## Implementation Gate

FastAPI model classes shall not be created until each schema above has a JSON schema file, at least one valid example, and a verification entry.
