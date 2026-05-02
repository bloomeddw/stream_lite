# REQ-010: FastAPI Control Plane Requirements

## Capability Intent

The FastAPI service shall provide the operational API for the system. It shall expose watcher management, job inspection, retry commands, health checks, event summaries, folder browsing and path validation, route tag normalization and preview, centralized dashboard presentation configuration, and log/query endpoints used by the Streamlit command center.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-API-001 | The API shall expose health endpoints for API readiness and dependency readiness. | Must | V-SL-API-001 |
| SL-API-002 | The API shall expose watcher create, list, read, and patch endpoints with documented schemas `WatcherCreateRequest`, `WatcherListResponse`, `WatcherDetailResponse`, and `WatcherPatchRequest`. | Must | V-SL-API-002 |
| SL-API-003 | The API shall expose watcher lifecycle endpoints: start, pause, resume, and stop. | Must | V-SL-API-003 |
| SL-API-004 | The API shall expose job list, job detail, and job state history endpoints. | Must | V-SL-API-004 |
| SL-API-005 | The API shall expose `POST /jobs/{job_id}/retry` for eligible failed jobs and return `409 JOB_NOT_RETRYABLE` for terminal states or failure codes that cannot be retried. | Must | V-SL-API-005 |
| SL-API-006 | The API shall validate request payloads using typed schemas. | Must | V-SL-API-006 |
| SL-API-007 | The API shall return machine-readable error responses with stable error codes. | Must | V-SL-API-007 |
| SL-API-008 | The API shall support pagination for job and log lists using `limit` and `offset`; default limit shall be `50`, maximum limit shall be `500`, and invalid values shall return `422 PAGINATION_INVALID`. | Must | V-SL-API-008 |
| SL-API-009 | The API shall support filtering jobs by watcher ID, state, terminal status, file name, and created timestamp range. | Must | V-SL-API-009 |
| SL-API-010 | The API shall expose summary metrics for dashboard cards. | Must | V-SL-API-010 |
| SL-API-011 | The API shall not execute arbitrary filesystem paths outside the configured allowlist. | Must | V-SL-API-011 |
| SL-API-012 | The API shall document endpoints through OpenAPI. | Must | V-SL-API-012 |
| SL-API-013 | The API shall expose a folder-browse endpoint that returns mounted, allowlisted candidate folders for dashboard source and destination selection. | Must | V-SL-API-013 |
| SL-API-014 | The API shall expose a folder-validation endpoint that validates a proposed source or destination path and returns `green`, `yellow`, or `red` status with reason code and operator-safe message. | Must | V-SL-API-014 |
| SL-API-015 | The API shall include source and destination health indicators in watcher read and list responses. | Must | V-SL-API-015 |
| SL-API-016 | Watcher create and update request schemas shall include route policy, source folder route tags, and destination folder route tags. | Must | V-SL-API-016 |
| SL-API-017 | The API shall validate route tags using the documented normalization and allowed-character rules before persisting watcher configuration. | Must | V-SL-API-017 |
| SL-API-018 | The API shall expose a route preview endpoint that returns the matched destination folders for each source folder before a watcher is enabled. | Must | V-SL-API-018 |
| SL-API-019 | The API shall reject enabling a watcher when any enabled source or destination folder has no valid normalized route tags. | Must | V-SL-API-019 |
| SL-API-020 | Watcher read and list responses shall include normalized tags, original tag text, match count, unmatched source/destination warnings, and latest route preview status. | Must | V-SL-API-020 |
| SL-API-021 | The API shall expose dashboard presentation configuration so the dashboard can load color tokens, status-dot colors, layout sections, and refresh behavior from a centralized contract. | Must | V-SL-API-021 |

## Minimum Endpoint Set

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | API health |
| GET | `/health/dependencies` | Database and broker health |
| POST | `/watchers` | Create watcher |
| GET | `/watchers` | List watchers |
| GET | `/watchers/{watcher_id}` | Read watcher |
| PATCH | `/watchers/{watcher_id}` | Update watcher |
| POST | `/watchers/{watcher_id}/start` | Start watcher |
| POST | `/watchers/{watcher_id}/pause` | Pause watcher |
| POST | `/watchers/{watcher_id}/resume` | Resume watcher |
| POST | `/watchers/{watcher_id}/stop` | Stop watcher |
| POST | `/watchers/{watcher_id}/preview-routes` | Preview tag-based source-to-destination matches before enabling a watcher |
| GET | `/jobs` | List jobs |
| GET | `/jobs/{job_id}` | Read job detail |
| GET | `/jobs/{job_id}/history` | Read state history |
| POST | `/jobs/{job_id}/retry` | Retry eligible job |
| GET | `/metrics/summary` | Dashboard summary metrics |
| GET | `/logs` | Operational log query |
| GET | `/files/browse` | List mounted allowlisted folders for source or destination selection |
| POST | `/files/validate-path` | Validate source or destination path and return health indicator |
| GET | `/config/dashboard-presentation` | Return dashboard color scheme, status tokens, layout configuration, and refresh defaults |
| GET | `/commands/{command_id}` | Read asynchronous command status and result |

## Route Tag API Contract

| Field | Requirement |
|---|---|
| `route_policy` | Shall default to `tag_match_all_destinations` for MVP. |
| `route_tags_text` | Shall accept semicolon-delimited operator input such as `A;B;CLIENT-001`. |
| `normalized_route_tags` | Shall contain the trimmed, uppercased, deduplicated tag list accepted by validation. |
| `tag_validation_errors` | Shall return stable error codes for empty tags, invalid characters, or missing tags. |
| `route_preview` | Shall list each source folder and the destination folders sharing at least one normalized tag. |
| `matched_route_tags` | Shall show which normalized tag or tags caused each source-destination match. |
| `unmatched_sources` | Shall identify sources with no matching destination and reason code `NO_MATCHING_DESTINATION`. |
| `unmatched_destinations` | Shall identify destinations with no matching source and reason code `NO_MATCHING_SOURCE`. |

## Dashboard Presentation Configuration API Contract

| Field | Requirement |
|---|---|
| `theme_name` | Shall identify the active dashboard theme. |
| `color_tokens` | Shall contain centrally managed semantic colors for success, warning, fault, neutral, background, text, accent, and disabled states. |
| `status_dot_tokens` | Shall map `green`, `yellow`, and `red` health states to theme-controlled display colors and labels. |
| `layout_profile` | Shall identify the active dashboard layout profile. |
| `layout_sections` | Shall define visible dashboard sections and their order without requiring scattered page-level constants. |
| `refresh_interval_seconds` | Shall provide the dashboard default refresh interval. |

## Folder Browse and Validation API Contract

| Field | Requirement |
|---|---|
| `purpose` | Shall be `source` or `destination`. |
| `path` | Shall be normalized and checked against the configured allowlist before use. |
| `status` | Shall be `green`, `yellow`, or `red`. |
| `reason_code` | Shall be a stable machine-readable code such as `OK`, `PENDING_CHECK`, `NOT_FOUND`, `NOT_ALLOWLISTED`, `NOT_READABLE`, or `NOT_WRITABLE`. |
| `message` | Shall be operator-safe and shall not expose host secrets or unmounted host paths. |

## Standard API Response Contract

| Area | Requirement |
|---|---|
| Success response | Mutation endpoints shall return `200` or `201` with the updated resource or command result; accepted asynchronous commands may return `202` with command ID. |
| Validation failure | Invalid request shape or invalid field value shall return `422` with `error_code`, `message`, `field`, and `correlation_id`. |
| State conflict | Invalid lifecycle or job state transitions shall return `409` with stable error code and current state. |
| Not found | Missing watcher, job, file, or log resource shall return `404` with stable error code. |
| Timeout target | API handlers shall complete within documented NFR targets or return `504 API_TIMEOUT` for dependency operations exceeding 10 seconds. |
| Idempotency | Watcher start, pause, resume, stop, and retry commands shall accept optional `Idempotency-Key`; duplicate keys for the same resource and payload shall return the first command result; duplicate keys for the same resource with a different payload shall return `409 IDEMPOTENCY_KEY_CONFLICT`. |
| Correlation | Every API response shall include or echo `correlation_id`; every mutation shall emit one structured log with route, method, status, duration_ms, and requirement ID group. |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-API-NFR-001 | Health endpoint p95 latency | <= 100 ms |
| SL-API-NFR-002 | Watcher mutation endpoint p95 latency | <= 300 ms |
| SL-API-NFR-003 | Job list endpoint p95 latency with <= 10,000 jobs | <= 300 ms |
| SL-API-NFR-004 | OpenAPI schema availability | 100% uptime when API ready |
| SL-API-NFR-005 | Request validation coverage for mutation endpoints | 100% |
| SL-API-NFR-006 | Folder validation endpoint p95 latency for local paths | <= 200 ms |
| SL-API-NFR-007 | Folder browse endpoint returns disallowed folders | 0 disallowed folders |
| SL-API-NFR-008 | Route preview endpoint p95 latency for <= 25 sources and <= 25 destinations | <= 300 ms |
| SL-API-NFR-009 | Dashboard presentation configuration availability | 100% when API ready |

## Acceptance Criteria

The requirement is accepted when the dashboard can operate entirely through documented API endpoints and API tests prove request validation, filtering, pagination, stable error codes, dependency health checks, folder browsing, path validation, route tag normalization, route preview generation, centralized dashboard presentation configuration, and source/destination health indicator responses.

## Expanded Control Plane Endpoint Contract Matrix

This L2 matrix aligns `REQ-010` with `docs/api/endpoints.md`. Schema names, log event names, metrics, status codes, and requirement IDs shall stay synchronized between the two files.

| Method | Path | Request schema | Response schema | Success | Primary errors | Idempotency | Timeout target | Log event | Metric | Related requirements |
|--------|---|---|---|---|---|---|---------------:|---|---|
| GET    | `/health` | none | `HealthResponse` | `200` | `503 SERVICE_NOT_READY` | not required |     100 ms p95 | `api.health_checked` | `stream_lite_api_request_duration_seconds` | SL-API-001 |
| GET    | `/health/dependencies` | none | `DependencyHealthResponse` | `200` or `503` | `503 DEPENDENCY_UNAVAILABLE` | not required |     300 ms p95 | `api.dependency_health_checked` | `stream_lite_api_dependency_status` | SL-RUN-013, SL-API-001 |
| POST   | `/watchers` | `WatcherCreateRequest` | `WatcherDetailResponse` | `201` | `422 PATH_NOT_ALLOWLISTED`, `422 TAG_INVALID`, `409 WATCHER_NAME_CONFLICT` | optional `Idempotency-Key` |     300 ms p95 | `api.watchers.create` | `stream_lite_api_request_duration_seconds` | SL-API-002, SL-FWM-020 |
| GET    | `/watchers` | query params | `WatcherListResponse` | `200` | `422 PAGINATION_INVALID` | not required |     300 ms p95 | `api.watchers.list` | `stream_lite_api_request_duration_seconds` | SL-API-002 |
| GET    | `/watchers/{watcher_id}` | path param | `WatcherDetailResponse` | `200` | `404 WATCHER_NOT_FOUND` | not required |     300 ms p95 | `api.watchers.read` | `stream_lite_api_request_duration_seconds` |  SL-API-002 |
| PATCH  | `/watchers/{watcher_id}` | `WatcherPatchRequest` | `WatcherDetailResponse` | `200` | `404 WATCHER_NOT_FOUND`, `422 TAG_INVALID`, `409 WATCHER_STATE_CONFLICT` | optional `Idempotency-Key` |     300 ms p95 | `api.watchers.patch` | `stream_lite_api_request_duration_seconds` | SL-API-002 |
| POST   | `/watchers/{watcher_id}/start` | `LifecycleCommandRequest` | `CommandAcceptedResponse` | `202` | `404 WATCHER_NOT_FOUND`, `409 ROUTE_NOT_ENABLED`, `409 WATCHER_STATE_CONFLICT`, `409 IDEMPOTENCY_KEY_CONFLICT` | optional `Idempotency-Key` |     300 ms p95 | `api.watchers.start` | `stream_lite_api_command_total` | SL-API-003, SL-LIFE-001 |
| POST   | `/watchers/{watcher_id}/pause` | `LifecycleCommandRequest` | `CommandAcceptedResponse` | `202` | `404 WATCHER_NOT_FOUND`, `409 WATCHER_STATE_CONFLICT`, `409 IDEMPOTENCY_KEY_CONFLICT` | optional `Idempotency-Key` |     300 ms p95 | `api.watchers.pause` | `stream_lite_api_command_total` | SL-API-003 |
| POST   | `/watchers/{watcher_id}/resume` | `LifecycleCommandRequest` | `CommandAcceptedResponse` | `202` | `404 WATCHER_NOT_FOUND`, `409 WATCHER_STATE_CONFLICT`, `409 IDEMPOTENCY_KEY_CONFLICT` | optional `Idempotency-Key` |     300 ms p95 | `api.watchers.resume` | `stream_lite_api_command_total` | SL-API-003 |
| POST   | `/watchers/{watcher_id}/stop` | `LifecycleCommandRequest` | `CommandAcceptedResponse` | `202` | `404 WATCHER_NOT_FOUND`, `409 WATCHER_STATE_CONFLICT`, `409 IDEMPOTENCY_KEY_CONFLICT` | optional `Idempotency-Key` |     300 ms p95 | `api.watchers.stop` | `stream_lite_api_command_total` | SL-API-003 |
| POST   | `/watchers/{watcher_id}/preview-routes` | `RoutePreviewRequest` | `RoutePreviewResponse` | `200` | `404 WATCHER_NOT_FOUND`, `422 TAG_INVALID` | not required |     300 ms p95 | `api.watchers.preview_routes` | `stream_lite_route_preview_total` | SL-API-003 |
| GET    | `/jobs` | query params | `JobListResponse` | `200` | `422 PAGINATION_INVALID`, `422 FILTER_INVALID` | not required |     300 ms p95 | `api.jobs.list` | `stream_lite_api_request_duration_seconds` | SL-API-004, SL-API-009 |
| GET    | `/jobs/{job_id}` | path param | `JobDetailResponse` | `200` | `404 JOB_NOT_FOUND` | not required |     300 ms p95 | `api.jobs.read` | `stream_lite_api_request_duration_seconds` | SL-API-004 |
| GET    | `/jobs/{job_id}/history` | path param | `JobHistoryResponse` | `200` | `404 JOB_NOT_FOUND` | not required |     300 ms p95 | `api.jobs.history` | `stream_lite_api_request_duration_seconds` | SL-API-004 |
| POST   | `/jobs/{job_id}/retry` | `RetryCommandRequest` | `CommandAcceptedResponse` | `202` | `404 JOB_NOT_FOUND`, `409 JOB_NOT_RETRYABLE`, `409 RETRY_LIMIT_EXHAUSTED`, `409 IDEMPOTENCY_KEY_CONFLICT`, `422 REQUEST_VALIDATION_FAILED` | optional `Idempotency-Key` |     300 ms p95 | `api.job.retry_requested` | `stream_lite_retry_command_total` |SL-API-005, SL-RET-012 |
| GET    | `/commands/{command_id}` | path param  | `CommandStatusResponse` | `200` | `404 COMMAND_NOT_FOUND` | read-only |     200 ms p95 | `api.commands.detail` | `stream_lite_api_request_duration_seconds` |  SL-LIFE-015 |
| GET    | `/events` | query params | `EventListResponse` | `200` | `422 PAGINATION_INVALID`, `422 FILTER_INVALID` | not required |     300 ms p95 | `api.events.list` | `stream_lite_api_request_duration_seconds` | SL-EVT-015, SL-API-032 |
| GET    | `/metrics/summary` | none | `MetricsSummaryResponse` | `200` | `503 METRICS_UNAVAILABLE` | not required |     300 ms p95 | `api.metrics.summary` | `stream_lite_api_request_duration_seconds` | SL-API-010 |
| GET    | `/logs` | query params | `OperationalLogListResponse` | `200` | `422 PAGINATION_INVALID`, `422 FILTER_INVALID` | not required |     500 ms p95 | `api.logs.list` | `stream_lite_api_request_duration_seconds` | SL-OBS-008 |
| GET    | `/files/browse` | query params | `FolderBrowseResponse` | `200` | `422 PURPOSE_INVALID`, `503 PATH_ROOT_UNAVAILABLE` | not required |     200 ms p95 | `api.files.browse` | `stream_lite_api_request_duration_seconds` | SL-API-013
| POST   | `/files/validate-path` | `PathValidationRequest` | `PathValidationResponse` | `200` | `422 PURPOSE_INVALID`, `422 PATH_SYNTAX_INVALID` | optional `Idempotency-Key` |     200 ms p95 | `api.files.validate_path` | `stream_lite_path_validation_total` | SL-API-014, SL-SEC-001 |
| GET    | `/config/dashboard-presentation` | none | `DashboardPresentationResponse` | `200` | `500 PRESENTATION_CONFIG_INVALID` | not required |     300 ms p95 | `api.config.dashboard_presentation` | `stream_lite_api_request_duration_seconds` | SL-API-021, SL-UI-004 |
## Control Plane Boundary Contract

These L2 requirements decompose API boundary behavior that applies across endpoint groups.

| ID | Level | Requirement | Priority | Verification |
|---|---|---|---:|---|
| SL-API-022 | L2 | The API shall accept commands, persist command intent or resource changes, and return command/resource responses; it shall not execute watcher polling, Spark processing, validation scanning, or delivery file copies inline in request handlers. | Must | V-SL-API-022 |
| SL-API-023 | L2 | Every asynchronous command returning `202` shall include `command_id`, `accepted_at`, `status`, `resource_type`, `resource_id`, and `correlation_id`. | Must | V-SL-API-023 |
| SL-API-024 | L2 | Every mutation endpoint shall record an audit log row or operational log summary row with actor value `local_operator`, route, method, status code, resource ID when known, and correlation ID. | Must | V-SL-API-024 |
| SL-API-025 | L2 | API schemas shall be treated as control-plane contracts and shall be versioned or compatibility-checked under REQ-016 before route handlers are implemented. | Must | V-SL-API-025 |
| SL-API-026 | L2 | The API shall expose `GET /commands/{command_id}` so the dashboard can distinguish command acceptance from command completion. | Must | V-SL-API-026 |
| SL-API-027 | L2 | Watcher `pause` shall prevent new file detection for the watcher and shall not interrupt already registered jobs. | Must | V-SL-API-027 |
| SL-API-028 | L2 | Watcher `stop` shall prevent new file detection and mark the watcher lifecycle state `stopped`; already registered jobs shall continue according to their current stage unless a later cancellation requirement is added. | Must | V-SL-API-028 |
| SL-API-029 | L2 | Watcher `resume` shall be accepted only from `PAUSED`; watcher `start` shall be accepted only from `CREATED`, `STOPPED`, or `ERROR` after validation passes; invalid lifecycle commands shall return `409 WATCHER_STATE_CONFLICT`. | Must | V-SL-API-029 |
| SL-API-030 | L2 | Repeated lifecycle or retry commands with the same `Idempotency-Key`, same target resource, and same payload hash shall return the existing active or completed command response instead of creating a second command; the same key with a different payload hash shall return `409 IDEMPOTENCY_KEY_CONFLICT`. | Must | V-SL-API-030 |

## Endpoint Decomposition Requirements

These L2 requirements decompose endpoint contracts in `docs/api/endpoints.md`. They remain in `REQ-010` because they define control-plane behavior.

| ID | Level | Requirement | Priority | Verification |
|---|---|---|---:|---|
| SL-API-031 | L2 | The OpenAPI document shall expose the same schema names listed in `docs/schemas/api_schemas.md` and `docs/api/endpoints.md`; schema names shall not be generated with implementation-specific suffixes that differ from the documented contract. | Must | V-SL-API-031 |
| SL-API-032 | L2 | The API shall expose `GET /events` for dashboard event inspection with filters `watcher_id`, `job_id`, `event_type`, `from_occurred_at`, `to_occurred_at`, `limit`, and `offset`; invalid filters shall return `422 FILTER_INVALID` or `422 PAGINATION_INVALID`. | Must | V-SL-API-032 |
| SL-API-033 | L2 | Asynchronous command responses shall use `202` only after a command record is persisted with initial status `accepted`; accepted commands shall later transition to `running`, `succeeded`, `failed`, or `expired`. | Must | V-SL-API-033 |
| SL-API-034 | L2 | Watcher read and list responses shall include `watcher_id`, `name`, lifecycle state, operational status, source summaries, destination summaries, route preview status, created timestamp, updated timestamp, and `correlation_id`. | Must | V-SL-API-034 |
| SL-API-035 | L2 | Job detail responses shall include source identity, current state, latest transition, validation summary, processing attempt summary, destination delivery outcomes, latest retry schedule if present, latest error if present, and `correlation_id`. | Must | V-SL-API-035 |
| SL-API-036 | L2 | Mutation endpoints that start, pause, resume, stop, or retry work shall persist command intent before enqueueing work or returning success to the dashboard. | Must | V-SL-API-036 |
| SL-API-037 | L2 | Lifecycle and retry command endpoints shall accept missing `Idempotency-Key` by creating a new command, but the Streamlit dashboard shall supply `Idempotency-Key`; duplicate keys for the same resource and payload shall return the original command response, and duplicate keys for the same resource with a different payload shall return `409 IDEMPOTENCY_KEY_CONFLICT`. | Must | V-SL-API-037 |
| SL-API-038 | L2 | List endpoints shall order results deterministically: jobs by `created_at` descending then `job_id` ascending, events by `occurred_at` descending then `event_id` ascending, and logs by `created_at` descending then `log_summary_id` ascending. | Must | V-SL-API-038 |
| SL-API-039 | L2 | Every error response shall use the standard error envelope fields `error_code`, `message`, `field`, `resource_id`, `current_state`, and `correlation_id`; fields without a value shall be serialized as `null`, not omitted. | Must | V-SL-API-039 |
| SL-API-040 | L2 | Endpoint rows in `docs/api/endpoints.md` and the expanded matrix in this file shall be updated in the same patch when method, path, schema, status code, log event, metric, timeout, or requirement mapping changes. | Must | V-SL-API-040 |

## L3 API Implementation Trace Requirements

These L3 requirements name implementation surfaces expected once code begins. Function and module names may be adjusted by an explicit design decision, but the behaviors and traceability shall remain requirements-backed.

| ID | Level | L2 source | Implementation surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-API-041 | L3 | SL-API-001 | `stream_lite.api.routes.health.get_health` | The health handler shall return `HealthResponse`, include `correlation_id`, emit `api.health_checked`, and record `stream_lite_api_request_duration_seconds`. | V-SL-API-041 |
| SL-API-042 | L3 | SL-API-001, SL-RUN-013 | `stream_lite.api.routes.health.get_dependency_health` | The dependency health handler shall check PostgreSQL and Redis Streams readiness, return `DependencyHealthResponse`, and return 503 when a required dependency is unavailable. | V-SL-API-042 |
| SL-API-043 | L3 | SL-API-002, SL-FWM-020 | `stream_lite.api.routes.watchers.create_watcher` | The watcher create handler shall validate paths, route tags, route preview viability, and persist watcher configuration before returning `WatcherDetailResponse`. | V-SL-API-043 |
| SL-API-044 | L3 | SL-API-003, SL-API-022, SL-API-036 | `stream_lite.api.routes.watchers.request_lifecycle_command` | Watcher lifecycle command handlers shall persist command intent, apply lifecycle precondition validation, and return `CommandAcceptedResponse` without polling folders inline. | V-SL-API-044 |
| SL-API-045 | L3 | SL-API-004, SL-API-035 | `stream_lite.api.routes.jobs.get_job_detail` | The job detail handler shall assemble current state, validation summary, processing attempts, delivery outcomes, retry schedule, and latest error from metadata records. | V-SL-API-045 |
| SL-API-046 | L3 | SL-API-005, SL-RET-012, SL-API-036 | `stream_lite.api.routes.jobs.request_retry` | The retry handler shall reject non-retryable jobs, persist retry command intent for eligible jobs, and return `CommandAcceptedResponse` with command ID. | V-SL-API-046 |
| SL-API-047 | L3 | SL-API-026, SL-LIFE-015 | `stream_lite.api.routes.commands.get_command_status` | The command status handler shall return the latest command state and result without re-executing the command. | V-SL-API-047 |
| SL-API-048 | L3 | SL-EVT-015, SL-API-032 | `stream_lite.api.routes.events.list_events` | The event list handler shall read persisted event metadata, apply documented filters and pagination, and never read Redis Streams directly for dashboard inspection. | V-SL-API-048 |
| SL-API-049 | L3 | SL-API-013 | `stream_lite.api.routes.files.browse_folders` | The folder browse handler shall return only mounted allowlisted source or destination candidates and shall not expose disallowed host paths. | V-SL-API-049 |
| SL-API-050 | L3 | SL-API-014, SL-SEC-001 | `stream_lite.api.routes.files.validate_path` | The path validation handler shall normalize the proposed path, check allowlist and access status, and return green/yellow/red health with stable reason code. | V-SL-API-050 |

## Endpoint Query and Payload Detail

| Endpoint | Required query/body behavior | Response behavior |
|---|---|---|
| `GET /health` | No query parameters. | Returns `ready` only when the API process can accept local requests; dependency failures are reported by `/health/dependencies`. |
| `GET /health/dependencies` | No query parameters. | Returns 200 when all required dependencies are healthy and 503 when any required dependency is unavailable; each dependency entry includes `name`, `status`, `checked_at`, and optional `error_code`. |
| `POST /watchers` | Body shall match `WatcherCreateRequest`; at least one source and destination are required; route tags and paths are validated before persistence. | Returns `201 WatcherDetailResponse` only after watcher configuration, sources, destinations, and route preview are persisted. |
| `PATCH /watchers/{watcher_id}` | Body shall match `WatcherPatchRequest`; empty body is rejected with `422 EMPTY_PATCH`; lifecycle-changing fields are not accepted through PATCH. | Returns updated `WatcherDetailResponse`; rejected updates leave prior watcher configuration unchanged. |
| `POST /watchers/{watcher_id}/start` | Body shall match `LifecycleCommandRequest`; route preview must be green for enabled sources before command acceptance. | Returns `202 CommandAcceptedResponse`; watcher work begins through command processing, not inside the request handler. |
| `POST /watchers/{watcher_id}/pause` | Body shall match `LifecycleCommandRequest`; only `ACTIVE` watchers may be paused. | Returns `202 CommandAcceptedResponse`; pause blocks new detection after command success and does not interrupt registered jobs. |
| `POST /watchers/{watcher_id}/resume` | Body shall match `LifecycleCommandRequest`; only `PAUSED` watchers may be resumed. | Returns `202 CommandAcceptedResponse`; resume allows new detection after command success. |
| `POST /watchers/{watcher_id}/stop` | Body shall match `LifecycleCommandRequest`; `CREATED`, `ACTIVE`, `PAUSED`, and `ERROR` watchers may be stopped. | Returns `202 CommandAcceptedResponse`; stop prevents new detection after command success and existing registered jobs continue. |
| `GET /jobs` | Supports `watcher_id`, `state`, `terminal`, `file_name`, `created_from`, `created_to`, `limit`, and `offset`. | Returns `JobListResponse` with deterministic ordering and total count for the filtered result set. |
| `GET /events` | Supports `watcher_id`, `job_id`, `event_type`, `from_occurred_at`, `to_occurred_at`, `limit`, and `offset`. | Returns persisted event summaries derived from the event outbox and consumed offsets; it shall not read Redis Streams directly from the dashboard. |
