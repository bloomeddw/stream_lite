# WP-05 Low-Reasoning Checklist

This checklist reduces Codex reasoning burden for **WP-05 FastAPI App Shell and Control Plane Routes**. It is documentation-only. It does not start WP-05 implementation.

## Required local environment

Codex shall use the existing repository virtual environment before running dependency-backed checks:

```powershell
cd C:\Users\asosa\stream_lite
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If activation is blocked by PowerShell policy, use the process-scoped bypass documented in `docs/implementation/development_environment.md`. Do not vendor dependencies into `.pytest_vendor/`, `pytest_vendor/`, or `wheelhouse/`.

## WP-05 implementation order

Implement in this order and stop after each layer passes its focused tests:

1. `app/api/dependencies.py`
   - `get_settings()`
   - `get_db_session()`
   - `get_path_policy()`
   - repository dependency helpers
   - correlation ID helper

2. `app/api/main.py`
   - `create_app()` only
   - include route modules
   - standard exception handlers

3. Health/config/file utility routes
   - `GET /health`
   - `GET /health/dependencies`
   - `GET /config/dashboard-presentation`
   - `GET /files/browse`
   - `POST /files/validate-path`

4. Read-only repository routes
   - `GET /watchers`
   - `GET /watchers/{watcher_id}`
   - `GET /jobs`
   - `GET /jobs/{job_id}`
   - `GET /jobs/{job_id}/history`
   - `GET /commands/{command_id}`
   - `GET /events`
   - `GET /metrics/summary`
   - `GET /logs`

5. Configuration mutation and command-acceptance routes
   - `POST /watchers`
   - `PATCH /watchers/{watcher_id}`
   - `POST /watchers/{watcher_id}/preview-routes`
   - watcher lifecycle command routes
   - `POST /jobs/{job_id}/retry`

Do not implement background behavior behind command routes. Command routes persist command intent only.

## Fixed module map

| Module | Allowed contents |
|---|---|
| `app/api/main.py` | app factory, router registration, exception handler registration |
| `app/api/dependencies.py` | settings/session/repository/path-policy/correlation helpers |
| `app/api/routes/health.py` | health and dependency-health routes only |
| `app/api/routes/watchers.py` | watcher config, list/detail, lifecycle command acceptance, route preview |
| `app/api/routes/jobs.py` | job list/detail/history and retry command acceptance |
| `app/api/routes/commands.py` | command status lookup |
| `app/api/routes/events.py` | event list via WP-04 safe listing primitive only |
| `app/api/routes/files.py` | folder browse and path validation only |
| `app/api/routes/metrics.py` | metrics summary response only |
| `app/api/routes/operations.py` | operational log summary list only |
| `app/api/routes/config.py` | dashboard presentation config response only |
| `app/api/errors.py` | may add FastAPI exception conversion helpers only |

## Fixed route response rules

| Condition | Status | Error code |
|---|---:|---|
| Invalid request body/path/query schema | 422 | `REQUEST_VALIDATION_FAILED` unless a more specific documented code applies |
| Invalid pagination | 422 | `PAGINATION_INVALID` |
| Invalid filter | 422 | `FILTER_INVALID` |
| Empty watcher patch body | 422 | `EMPTY_PATCH` |
| Watcher not found | 404 | `WATCHER_NOT_FOUND` |
| Job not found | 404 | `JOB_NOT_FOUND` |
| Command not found | 404 | `COMMAND_NOT_FOUND` |
| Invalid lifecycle state transition | 409 | `INVALID_STATE_TRANSITION` |
| Path not allowlisted | 200 for validate-path red/yellow result; 422 only if request schema invalid | `PATH_NOT_ALLOWLISTED` in response body reason field where applicable |
| Dependency unavailable | 503 | `DEPENDENCY_UNAVAILABLE` |
| Metrics/log summary unavailable | 503 or 500 | `METRICS_UNAVAILABLE` or `LOGS_UNAVAILABLE` |

All standard error responses must include: `error_code`, `message`, `field`, `resource_id`, `current_state`, and `correlation_id`.

## Fixed repository use map

| Route group | Repository/service source |
|---|---|
| Watcher config routes | `WatcherRepository`; route preview helper local to API/service layer |
| Watcher lifecycle command routes | `WatcherRepository`, `CommandRepository`, idempotency repository from WP-03 if present |
| Job routes | `JobRepository`, validation/processing/delivery/retry repositories only for summary composition |
| Retry command route | `JobRepository`, `CommandRepository`, idempotency repository |
| Command status | `CommandRepository` |
| Events | `app.events.outbox.list_event_summaries` or equivalent WP-04 safe listing primitive |
| Files/path routes | WP-01 `PathPolicy` only; no file watcher behavior |
| Metrics/logs | existing summary repositories/placeholders only; do not scrape Prometheus unless already implemented |

## Fixed tests to create

| Test file | Required focus |
|---|---|
| `tests/api/test_app_factory.py` | app creates and includes expected route paths |
| `tests/api/test_health_routes.py` | `/health`, `/health/dependencies` schemas and status behavior |
| `tests/api/test_watcher_routes.py` | create/list/detail/patch/preview/lifecycle command acceptance |
| `tests/api/test_job_routes.py` | list/detail/history/retry command acceptance |
| `tests/api/test_command_routes.py` | command status success/not found |
| `tests/api/test_event_routes.py` | `GET /events` safe summaries and filters; no raw payload |
| `tests/api/test_file_routes.py` | browse and validate-path path safety |
| `tests/api/test_metrics_log_config_routes.py` | metrics, logs, dashboard presentation schemas |
| `tests/api/test_api_errors.py` | standard error shape, correlation ID propagation, pagination/filter errors |

## Stop conditions

Stop and ask for requirements clarification if WP-05 needs any of the following:

- a new API route not listed in `docs/api/endpoints.md`
- a new request or response schema
- a new env var
- a new database table or migration
- worker/background execution
- Redis stream reads from API route handlers
- direct filesystem watching or file processing
- Streamlit pages
