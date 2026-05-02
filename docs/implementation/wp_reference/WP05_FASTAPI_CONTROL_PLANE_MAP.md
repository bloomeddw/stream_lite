# WP-05 FastAPI Control Plane Implementation Map

## Purpose

This file is a code-ready planning artifact for **WP-05 FastAPI App Shell and Control Plane Routes**. It is intentionally documentation-only and does not start WP-04 or WP-05 implementation. Its purpose is to reduce Codex reasoning burden after WP-04 by giving a fixed route-to-module, schema, repository, service, test, and evidence map.

WP-05 SHALL start only after WP-04 is complete and verified. WP-05 SHALL not add watcher polling, validation/quarantine workers, processing workers, delivery workers, retry scheduler loops, Streamlit pages, or new migrations.

## Low-Reasoning Checklist

Before implementing WP-05, Codex shall read `docs/implementation/wp_reference/WP05_LOW_REASONING_CHECKLIST.md` and follow its fixed implementation order, route response rules, repository use map, required tests, and stop conditions. This avoids re-deriving routing, dependency, and error behavior from multiple documents.

## WP-05 Scope Boundary

| In scope | Out of scope |
|---|---|
| FastAPI app factory and route modules | Worker/service execution loops |
| Dependency injection for settings, DB session, repositories, path policy, event services, and observability primitives | Watcher file polling or filesystem detection |
| Documented API routes from `docs/api/endpoints.md` | Redis dispatcher implementation beyond using WP-04 primitives |
| Request/response validation using WP-02 Pydantic models | New event schemas or API schemas |
| Repository-backed reads and command intent persistence using WP-03 repositories | New database migrations unless a documented mismatch blocks route implementation |
| Event enqueue calls only where the existing contract requires command/event handoff | Streamlit UI pages |
| API tests for schemas, errors, idempotency, pagination, filters, and status codes | Docker Compose orchestration changes |

## Preconditions From Earlier Work Packages

| Work package | Required before WP-05 |
|---|---|
| WP-01 | Settings, path policy, standard error primitives, and logging bootstrap exist. |
| WP-02 | API Pydantic models validate every API example and preserve schema-facing field names. |
| WP-03 | SQLAlchemy models and repository primitives exist for watchers, jobs, commands, events, logs, and health. |
| WP-04 | Event outbox enqueueing, Redis stream client wrapper, dispatcher primitives, dead-letter handling, and event listing primitives exist. |

## FastAPI Dependency Map

Codex SHOULD implement or reuse these app-level dependencies. Names may differ only if the worklog documents the reason and preserves traceability.

| Dependency | Suggested function | Source | Used by |
|---|---|---|---|
| Settings | `get_settings()` | `app.config.settings.StreamLiteSettings` | all routes |
| DB session | `get_db_session()` | `app.db.session` | repository-backed routes |
| Correlation ID | `get_or_create_correlation_id()` | request header or generated UUID | all routes |
| Path policy | `get_path_policy()` | WP-01 path policy/settings | files and watcher routes |
| Repository bundle | `get_repositories()` or route-specific dependency functions | WP-03 repositories | watcher/job/event/log/health routes |
| Event outbox service | `get_event_outbox_service()` | WP-04 outbox primitive | lifecycle/retry command routes if event handoff is needed |
| Metrics recorder | `get_api_metrics()` | WP-01/WP-12 placeholder-safe primitive if present | all routes |
| Structured logger | `get_api_logger()` | `app.observability.logging` | all routes |

Do not add new environment variables for these dependencies. Use existing documented settings only.

## Route Implementation Map

| Route | Handler | Request model | Response model | Primary repository/service calls | Status/error behavior | Requirements | Tests |
|---|---|---|---|---|---|---|---|
| `GET /health` | `app.api.routes.health.get_health` | none | `HealthResponse` | settings/version only | 200, no dependency probe | SL-API-041 | `test_get_health_returns_schema` |
| `GET /health/dependencies` | `app.api.routes.health.get_dependency_health` | none | `DependencyHealthResponse` | DB session ping; Redis readiness wrapper from WP-04 if available; filesystem root checks through path policy | 200 when all required dependencies ready, 503 when required dependency unavailable | SL-API-042, SL-RUN-013 | `test_dependency_health_ready`, `test_dependency_health_unavailable_returns_503` |
| `POST /watchers` | `app.api.routes.watchers.create_watcher` | `WatcherCreateRequest` | `WatcherDetailResponse` | `WatcherRepository.create_watcher`, `replace_sources`, `replace_destinations`, `save_route_preview`, path policy validation, route preview helper | 201; 422 path/tag errors; no file polling | SL-API-043, SL-FWM-020 | `test_create_watcher_persists_config`, `test_create_watcher_rejects_bad_path` |
| `GET /watchers` | `app.api.routes.watchers.list_watchers` | query `limit`, `offset` | `WatcherListResponse` | `WatcherRepository.list_watchers` | 200; 422 `PAGINATION_INVALID` | SL-API-034, SL-API-038 | `test_list_watchers_paginates` |
| `GET /watchers/{watcher_id}` | `app.api.routes.watchers.get_watcher` | path UUID | `WatcherDetailResponse` | `WatcherRepository.get_watcher`, source/destination/route match reads | 200; 404 `WATCHER_NOT_FOUND` | SL-API-034 | `test_get_watcher_not_found` |
| `PATCH /watchers/{watcher_id}` | `app.api.routes.watchers.patch_watcher` | `WatcherPatchRequest` | `WatcherDetailResponse` | `WatcherRepository.get_watcher`, replacement methods for supplied fields, route preview recompute | 200; 404; 409 state conflict; 422 `EMPTY_PATCH` | SL-API-034, SL-API-039 | `test_patch_watcher_empty_body_rejected`, `test_patch_watcher_updates_sources` |
| `POST /watchers/{watcher_id}/start` | `app.api.routes.watchers.start_watcher` | `LifecycleCommandRequest` | `CommandAcceptedResponse` | `WatcherRepository.get_watcher`, `CommandRepository.create_command`, idempotency key reservation | 202 after command persisted; 404; 409 invalid state | SL-API-044, SL-API-033, SL-API-036, SL-API-037 | `test_start_persists_command`, `test_start_idempotency_reuses_command` |
| `POST /watchers/{watcher_id}/pause` | `app.api.routes.watchers.pause_watcher` | `LifecycleCommandRequest` | `CommandAcceptedResponse` | same command acceptance path | 202; 404; 409 invalid state | SL-API-044 | `test_pause_rejects_created_state` |
| `POST /watchers/{watcher_id}/resume` | `app.api.routes.watchers.resume_watcher` | `LifecycleCommandRequest` | `CommandAcceptedResponse` | same command acceptance path | 202; 404; 409 invalid state | SL-API-044 | `test_resume_requires_paused_state` |
| `POST /watchers/{watcher_id}/stop` | `app.api.routes.watchers.stop_watcher` | `LifecycleCommandRequest` | `CommandAcceptedResponse` | same command acceptance path | 202; 404; 409 invalid state | SL-API-044 | `test_stop_accepts_active_state` |
| `POST /watchers/{watcher_id}/preview-routes` | `app.api.routes.watchers.preview_routes` | `RoutePreviewRequest` | `RoutePreviewResponse` | route preview helper only; no repository write unless current docs explicitly require preview persistence | 200; 404; 422 tag/path errors | SL-API-018, SL-FWM-039 | `test_preview_routes_returns_unmatched_sources` |
| `GET /jobs` | `app.api.routes.jobs.list_jobs` | query filters | `JobListResponse` | `JobRepository.list_jobs` | 200; 422 `FILTER_INVALID` or `PAGINATION_INVALID`; deterministic ordering | SL-API-004, SL-API-038 | `test_list_jobs_filters_and_orders` |
| `GET /jobs/{job_id}` | `app.api.routes.jobs.get_job_detail` | path UUID | `JobDetailResponse` | `JobRepository.get_job`, state history, validation, processing, delivery, retry repositories | 200; 404 `JOB_NOT_FOUND` | SL-API-045 | `test_get_job_detail_composes_summary` |
| `GET /jobs/{job_id}/history` | `app.api.routes.jobs.get_job_history` | path UUID | `JobHistoryResponse` | `JobRepository.list_state_history` | 200; 404 | SL-API-004 | `test_get_job_history_returns_entries` |
| `POST /jobs/{job_id}/retry` | `app.api.routes.jobs.request_retry` | `RetryCommandRequest` | `CommandAcceptedResponse` | `JobRepository.get_job`, `CommandRepository.create_command`, idempotency reservation; no retry execution | 202; 404; 409/422 not retryable | SL-API-046, SL-RET-012 | `test_retry_persists_command`, `test_retry_rejects_non_retryable_job` |
| `GET /commands/{command_id}` | `app.api.routes.commands.get_command_status` | path UUID | `CommandStatusResponse` | `CommandRepository.get_command` | 200; 404 `COMMAND_NOT_FOUND` | SL-API-047, SL-LIFE-015 | `test_get_command_status` |
| `GET /events` | `app.api.routes.events.list_events` | query filters | `EventListResponse` | WP-04 event listing primitive or `EventOutboxRepository` safe summary method | 200; 422 filter/pagination errors; never read Redis directly | SL-API-048, SL-EVT-015 | `test_list_events_returns_safe_summary` |
| `GET /metrics/summary` | `app.api.routes.metrics.get_metrics_summary` | none | `MetricsSummaryResponse` | summary repository/read model only; no Prometheus scrape parsing required unless implemented | 200; 503/500 `METRICS_UNAVAILABLE` | SL-API-010, SL-OBS-006 | `test_metrics_summary_schema` |
| `GET /logs` | `app.api.routes.operations.list_logs` | query filters | `OperationalLogListResponse` | `OperationalLogRepository.list_summaries` | 200; 422 filter/pagination errors | SL-OBS-008 | `test_list_logs_sanitizes_paths` |
| `GET /files/browse` | `app.api.routes.files.browse_folders` | query `purpose`, optional `root` | `FolderBrowseResponse` | path policy/filesystem listing constrained to allowlisted roots | 200; 422/404 `PATH_ROOT_UNAVAILABLE`; no disallowed host paths | SL-API-049, SL-SEC-001 | `test_browse_folders_only_allowlisted` |
| `POST /files/validate-path` | `app.api.routes.files.validate_path` | `PathValidationRequest` | `PathValidationResponse` | WP-01 path policy | 200 with green/yellow/red status; 422 only for request schema violation | SL-API-050, SL-SEC-001 | `test_validate_path_uses_path_policy` |
| `GET /config/dashboard-presentation` | `app.api.routes.config.get_dashboard_presentation` | none | `DashboardPresentationResponse` | static/default dashboard presentation provider or repository if already implemented | 200; 500 `PRESENTATION_CONFIG_INVALID` | SL-API-021, SL-UI-004 | `test_dashboard_presentation_schema` |

## Shared Route Helper Map

| Helper | Suggested location | Required behavior | Tests |
|---|---|---|---|
| Pagination parser | `app/api/dependencies.py` | Default `limit=50`, max `500`, `offset>=0`; invalid returns standard error with `PAGINATION_INVALID`. | `test_pagination_dependency_rejects_invalid_limit` |
| Filter parser | route modules or dependency helpers | Reject invalid UUIDs, enums, and timestamp ranges with `FILTER_INVALID`. | `test_event_filter_invalid_timestamp` |
| Standard error response builder | `app/api/errors.py` or `app/api/dependencies.py` | Serialize all standard error fields, including null fields. | `test_standard_error_response_shape` |
| Idempotency key reader | `app/api/dependencies.py` | Read `Idempotency-Key`; allow missing but command routes should reserve when supplied. | `test_command_idempotency_key_reuse` |
| Command acceptance helper | `app/api/routes/watchers.py` or `app/api/routes/commands.py` | Persist command before returning 202; no inline worker execution. | command route tests |
| Watcher response assembler | `app/api/routes/watchers.py` or helper module | Convert repository records into `WatcherDetailResponse` exactly. | watcher route tests |
| Job detail assembler | `app/api/routes/jobs.py` or helper module | Compose source, destinations, attempt summary, latest error, and correlation ID. | job route tests |
| Route preview helper | `app/api/routes/watchers.py` or `app/watcher/routing.py` if already present | Compute tag matches without touching filesystem or creating jobs. | route preview tests |

## Standard Error Mapping

| Condition | Status | Error code |
|---|---:|---|
| Invalid pagination | 422 | `PAGINATION_INVALID` |
| Invalid query filter | 422 | `FILTER_INVALID` |
| Invalid/unsafe path | 422 | `PATH_INVALID` or `PATH_NOT_ALLOWLISTED` |
| Invalid route tag | 422 | `TAG_INVALID` |
| Empty watcher patch body | 422 | `EMPTY_PATCH` |
| Missing watcher | 404 | `WATCHER_NOT_FOUND` |
| Missing job | 404 | `JOB_NOT_FOUND` |
| Missing command | 404 | `COMMAND_NOT_FOUND` |
| Invalid watcher lifecycle transition | 409 | `INVALID_WATCHER_STATE` or documented alias already used in schema/tests |
| Watcher route cannot start because routing is not green | 409 | `ROUTE_NOT_ENABLED` |
| Job is not retryable | 409 | `JOB_NOT_RETRYABLE` |
| Retry attempts exhausted | 409 | `RETRY_LIMIT_EXHAUSTED` |
| Metrics summary unavailable | 503 | `METRICS_UNAVAILABLE` |
| Presentation configuration invalid | 500 | `PRESENTATION_CONFIG_INVALID` |

If existing code/tests use a different active error code, Codex SHALL align requirements/docs/tests in the same patch or stop and ask for clarification. Do not silently invent aliases.

## Test Package Map

Create focused tests under `tests/api/`.

| Test file | Main coverage |
|---|---|
| `tests/api/test_app_factory.py` | FastAPI app creation, route registration, OpenAPI schema names do not drift. |
| `tests/api/test_health_routes.py` | `/health`, `/health/dependencies`, dependency status mapping. |
| `tests/api/test_watcher_routes.py` | watcher create/list/get/patch/preview and lifecycle command acceptance. |
| `tests/api/test_job_routes.py` | job list/detail/history/retry command acceptance. |
| `tests/api/test_command_routes.py` | command status retrieval and not found behavior. |
| `tests/api/test_event_routes.py` | event list filters, pagination, safe summaries from outbox metadata. |
| `tests/api/test_file_routes.py` | folder browse and path validation with allowlist behavior. |
| `tests/api/test_metrics_log_config_routes.py` | metrics summary, operational logs, dashboard presentation response schema. |
| `tests/api/test_api_errors.py` | error envelope completeness, correlation ID propagation, no secret/path leakage. |

Use FastAPI `TestClient` or `httpx` only inside WP-05 route tests. Prefer SQLite-backed repository fixtures from WP-03 for repository-backed route behavior.

## Minimal Dependency Guidance

WP-05 may add FastAPI test/runtime dependencies if not already present:

| Dependency | File | Reason |
|---|---|---|
| `fastapi>=0.110,<1` | `requirements.txt` | API app and route implementation. |
| `uvicorn>=0.29,<1` | `requirements.txt` or deferred if no server entrypoint is added | Local manual serving only; route tests do not need it. |
| `httpx>=0.27,<1` | `requirements-dev.txt` | FastAPI/TestClient support if needed. |

Do not add new environment variables for WP-05.

## WP-05 Completion Checklist

- FastAPI app factory exists and includes documented route modules.
- All routes in `docs/api/endpoints.md` are implemented or explicitly deferred by requirement-backed reason.
- Route request/response models reuse WP-02 Pydantic models.
- Repository-backed routes use WP-03 repository primitives.
- Event listing uses persisted outbox metadata or WP-04 safe listing primitive, not Redis reads.
- Mutation command routes persist command intent before returning `202`.
- Standard errors include every field and propagate `correlation_id`.
- Pagination/filter validation matches `REQ-010`.
- OpenAPI schema names remain aligned with `docs/schemas/api_schemas.md`.
- Existing WP-00 through WP-04 verification still passes.
- New API route tests pass.
- No generated/cache/vendor artifacts are included.
- WP-06 is not started.
