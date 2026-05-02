# Streamlit Control Matrix

The Streamlit dashboard is an operator command center. It shall not mutate PostgreSQL, Redis, or filesystem state directly. All mutations go through FastAPI.

| Dashboard control/view | API route | Request schema | Allowed states | Validation rule | Success response | Failure response | Log event | Metric | Requirements |
|---|---|---|---|---|---|---|---|---|---|
| Create watcher | `POST /watchers` | `WatcherCreateRequest` | n/a | paths allowlisted, tags valid, at least one matched destination | `201 WatcherDetailResponse` | `422`, `409` standard error | `watcher.create_requested` | `stream_lite_dashboard_action_total{action="create_watcher"}` | SL-UI-001, SL-API-002 |
| Edit watcher | `PATCH /watchers/{watcher_id}` | `WatcherPatchRequest` | non-deleted watcher | same as create; active edits limited to non-breaking fields until future requirement expands | `200 WatcherDetailResponse` | `404`, `409`, `422` | `watcher.patch_requested` | `stream_lite_dashboard_action_total{action="edit_watcher"}` | SL-UI-001 |
| Start watcher | `POST /watchers/{watcher_id}/start` | `LifecycleCommandRequest` | `created`, `stopped`, `paused`, `error` when route valid | route preview not red; source/destination health not blocking | `202 CommandAcceptedResponse` then command success | `409 ROUTE_NOT_ENABLED`, `WATCHER_STATE_CONFLICT` | `watcher.start_requested` | `stream_lite_dashboard_action_total{action="start_watcher"}` | SL-UI-003, SL-LIFE-001 |
| Pause watcher | `POST /watchers/{watcher_id}/pause` | `LifecycleCommandRequest` | `active` | pause blocks new detection only | `202 CommandAcceptedResponse` | `409 WATCHER_STATE_CONFLICT` | `watcher.pause_requested` | `stream_lite_dashboard_action_total{action="pause_watcher"}` | SL-FWM-010 |
| Resume watcher | `POST /watchers/{watcher_id}/resume` | `LifecycleCommandRequest` | `paused` | route preview still valid | `202 CommandAcceptedResponse` | `409 WATCHER_STATE_CONFLICT` | `watcher.resume_requested` | `stream_lite_dashboard_action_total{action="resume_watcher"}` | SL-FWM-010 |
| Stop watcher | `POST /watchers/{watcher_id}/stop` | `LifecycleCommandRequest` | `active`, `paused`, `error` | stop blocks new detection; registered jobs continue | `202 CommandAcceptedResponse` | `409 WATCHER_STATE_CONFLICT` | `watcher.stop_requested` | `stream_lite_dashboard_action_total{action="stop_watcher"}` | SL-FWM-010 |
| Preview routes | `POST /watchers/{watcher_id}/preview-routes` or unsaved preview payload | `RoutePreviewRequest` | any editable watcher | route tags normalize and match policy | `200 RoutePreviewResponse` | `422 TAG_INVALID` | `route.preview_requested` | `stream_lite_route_preview_total` | SL-FWM-026 |
| Validate path | `POST /files/validate-path` | `PathValidationRequest` | n/a | purpose source/destination and allowlist check | `200 PathValidationResponse` | `422 PATH_INVALID` | `files.path_validated` | `stream_lite_path_validation_total` | SL-API-014 |
| Retry job | `POST /jobs/{job_id}/retry` | `RetryCommandRequest` | eligible failed processing/delivery job | retry eligibility table in retry policy | `202 CommandAcceptedResponse` | `409 JOB_NOT_RETRYABLE` | `job.retry_requested` | `stream_lite_retry_command_total` | SL-API-005 |
| View jobs | `GET /jobs` | query | n/a | pagination limits | `200 JobListResponse` | `422 PAGINATION_INVALID` | `job.list_requested` | `stream_lite_api_request_duration_seconds` | SL-UI-006 |
| View job history | `GET /jobs/{job_id}/history` | path | existing job | n/a | `200 JobHistoryResponse` | `404 JOB_NOT_FOUND` | `job.history_requested` | `stream_lite_api_request_duration_seconds` | SL-UI-006 |
| View events | `GET /events` | query | n/a | pagination limits | `200 EventListResponse` | `422 PAGINATION_INVALID` | `event.list_requested` | `stream_lite_api_request_duration_seconds` | SL-UI-007 |
| View logs | `GET /logs` | query | n/a | pagination/filter limits | `200 OperationalLogListResponse` | `422 FILTER_INVALID` | `log.list_requested` | `stream_lite_api_request_duration_seconds` | SL-UI-010 |
| View metrics summary | `GET /metrics/summary` | none | n/a | n/a | `200 MetricsSummaryResponse` | `503 METRICS_UNAVAILABLE` | `metrics.summary_requested` | `stream_lite_api_request_duration_seconds` | SL-UI-009 |
| Load theme/layout | `GET /config/dashboard-presentation` | none | API ready | YAML validates schema | `200 DashboardPresentationResponse` | local read-only fallback with yellow banner | `config.dashboard_presentation_requested` | `stream_lite_api_request_duration_seconds` | SL-UI-004 |

## Feedback Rules

- Every mutation control shall show accepted, running, succeeded, failed, or expired command state when the API returns `202`.
- Controls shall disable actions that the latest API state marks invalid.
- Yellow states shall be warnings, not hidden errors.
- Red states shall include the stable reason code and operator-safe message.
