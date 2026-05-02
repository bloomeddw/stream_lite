# Stream Lite API Endpoint Contract

All v0.1 routes are local-demo routes and are unauthenticated unless a later requirement activates authentication. Every response shall include `correlation_id`. Mutation routes shall write a structured API log event and shall record an idempotency key when supplied.

## Standard Error Envelope

```json
{
  "error_code": "TAG_INVALID",
  "message": "Operator-safe message.",
  "field": "sources[0].route_tags_text",
  "resource_id": "uuid-or-null",
  "current_state": "ACTIVE-or-null",
  "correlation_id": "uuid"
}
```

## Endpoint Matrix

| Method | Path | Owner | Request schema | Success schema | Success | Primary errors | Idempotency | Timeout | Log event | Metric | Requirements |
|---|---|---|---|---|---:|---|---|---:|---|---|---|
| GET | `/health` | API | none | `HealthResponse` | 200 | none | n/a | 100 ms | `api.health_checked` | `stream_lite_api_request_duration_seconds` | SL-API-001 |
| GET | `/health/dependencies` | API | none | `DependencyHealthResponse` | 200/503 | `DB_UNAVAILABLE`, `BROKER_UNAVAILABLE` | n/a | 500 ms | `api.dependency_health_checked` | `stream_lite_api_dependency_status` | SL-RUN-013, SL-API-001 |
| POST | `/watchers` | API | `WatcherCreateRequest` | `WatcherDetailResponse` | 201 | `PATH_NOT_ALLOWLISTED`, `TAG_INVALID`, `NO_MATCHING_DESTINATION` | optional | 300 ms | `watcher.create_requested` | `stream_lite_api_request_duration_seconds` | SL-API-002, SL-FWM-020 |
| GET | `/watchers` | API | query | `WatcherListResponse` | 200 | `PAGINATION_INVALID` | n/a | 300 ms | `watcher.list_requested` | `stream_lite_api_request_duration_seconds` | SL-API-002 |
| GET | `/watchers/{watcher_id}` | API | path | `WatcherDetailResponse` | 200 | `WATCHER_NOT_FOUND` | n/a | 200 ms | `watcher.read_requested` | `stream_lite_api_request_duration_seconds` | SL-API-002 |
| PATCH | `/watchers/{watcher_id}` | API | `WatcherPatchRequest` | `WatcherDetailResponse` | 200 | `WATCHER_NOT_FOUND`, `WATCHER_STATE_CONFLICT`, `TAG_INVALID` | optional | 300 ms | `watcher.patch_requested` | `stream_lite_api_request_duration_seconds` | SL-API-002 |
| POST | `/watchers/{watcher_id}/start` | API + watcher | `LifecycleCommandRequest` | `CommandAcceptedResponse` | 202 | `WATCHER_NOT_FOUND`, `ROUTE_NOT_ENABLED`, `WATCHER_STATE_CONFLICT`, `IDEMPOTENCY_KEY_CONFLICT` | required recommended | 300 ms | `watcher.start_requested` | `stream_lite_api_command_total` | SL-API-003, SL-LIFE-001 |
| POST | `/watchers/{watcher_id}/pause` | API + watcher | `LifecycleCommandRequest` | `CommandAcceptedResponse` | 202 | `WATCHER_NOT_FOUND`, `WATCHER_STATE_CONFLICT`, `IDEMPOTENCY_KEY_CONFLICT` | required recommended | 300 ms | `watcher.pause_requested` | `stream_lite_api_command_total` | SL-API-003 |
| POST | `/watchers/{watcher_id}/resume` | API + watcher | `LifecycleCommandRequest` | `CommandAcceptedResponse` | 202 | `WATCHER_NOT_FOUND`, `WATCHER_STATE_CONFLICT`, `IDEMPOTENCY_KEY_CONFLICT` | required recommended | 300 ms | `watcher.resume_requested` | `stream_lite_api_command_total` | SL-API-003 |
| POST | `/watchers/{watcher_id}/stop` | API + watcher | `LifecycleCommandRequest` | `CommandAcceptedResponse` | 202 | `WATCHER_NOT_FOUND`, `WATCHER_STATE_CONFLICT`, `IDEMPOTENCY_KEY_CONFLICT` | required recommended | 300 ms | `watcher.stop_requested` | `stream_lite_api_command_total` | SL-API-003 |
| POST | `/watchers/{watcher_id}/preview-routes` | API | `RoutePreviewRequest` | `RoutePreviewResponse` | 200 | `WATCHER_NOT_FOUND`, `TAG_INVALID` | n/a | 300 ms | `route.preview_requested` | `stream_lite_route_preview_total` | SL-API-018 |
| GET | `/jobs` | API | query | `JobListResponse` | 200 | `PAGINATION_INVALID`, `FILTER_INVALID` | n/a | 300 ms | `job.list_requested` | `stream_lite_api_request_duration_seconds` | SL-API-004, SL-API-009 |
| GET | `/jobs/{job_id}` | API | path | `JobDetailResponse` | 200 | `JOB_NOT_FOUND` | n/a | 200 ms | `job.read_requested` | `stream_lite_api_request_duration_seconds` | SL-API-004 |
| GET | `/jobs/{job_id}/history` | API | path | `JobHistoryResponse` | 200 | `JOB_NOT_FOUND` | n/a | 200 ms | `job.history_requested` | `stream_lite_api_request_duration_seconds` | SL-API-004 |
| POST | `/jobs/{job_id}/retry` | API + retry scheduler | `RetryCommandRequest` | `CommandAcceptedResponse` | 202 | `JOB_NOT_FOUND`, `JOB_NOT_RETRYABLE`, `RETRY_LIMIT_EXHAUSTED`, `IDEMPOTENCY_KEY_CONFLICT` | required recommended | 300 ms | `job.retry_requested` | `stream_lite_retry_command_total` | SL-API-005, SL-RET-012 |
| GET | `/commands/{command_id}` | API | path | `CommandStatusResponse` | 200 | `COMMAND_NOT_FOUND` | n/a | 200 ms | `command.read_requested` | `stream_lite_api_request_duration_seconds` | SL-LIFE-015 |
| GET | `/events` | API | query | `EventListResponse` | 200 | `PAGINATION_INVALID`, `FILTER_INVALID` | n/a | 300 ms | `event.list_requested` | `stream_lite_api_request_duration_seconds` | SL-EVT-015, SL-API-032 |
| GET | `/metrics/summary` | API | none | `MetricsSummaryResponse` | 200 | `METRICS_UNAVAILABLE` | n/a | 300 ms | `metrics.summary_requested` | `stream_lite_api_request_duration_seconds` | SL-API-010 |
| GET | `/logs` | API | query | `OperationalLogListResponse` | 200 | `PAGINATION_INVALID`, `FILTER_INVALID` | n/a | 300 ms | `log.list_requested` | `stream_lite_api_request_duration_seconds` | SL-OBS-008 |
| GET | `/files/browse` | API | query | `FolderBrowseResponse` | 200 | `PURPOSE_INVALID`, `PATH_ROOT_UNAVAILABLE` | n/a | 200 ms | `files.browse_requested` | `stream_lite_api_request_duration_seconds` | SL-API-013 |
| POST | `/files/validate-path` | API | `PathValidationRequest` | `PathValidationResponse` | 200 | `PATH_INVALID`, `PATH_NOT_ALLOWLISTED` | n/a | 200 ms | `files.path_validated` | `stream_lite_path_validation_total` | SL-API-014, SL-SEC-001 |
| GET | `/config/dashboard-presentation` | API | none | `DashboardPresentationResponse` | 200 | `PRESENTATION_CONFIG_INVALID` | n/a | 200 ms | `config.dashboard_presentation_requested` | `stream_lite_api_request_duration_seconds` | SL-API-021, SL-UI-004 |

## Async Command Contract

`202` means the API accepted and persisted command intent. It does not mean the watcher or retry scheduler completed the command. The dashboard shall poll `GET /commands/{command_id}` until `status` is `succeeded`, `failed`, or `expired`.

## Pagination Contract

List routes shall accept `limit` and `offset`. Default `limit` is `50`; maximum `limit` is `500`; negative `offset` or out-of-range `limit` returns `422 PAGINATION_INVALID`.
