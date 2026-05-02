# WORKLOG-20260501-wp05-fastapi-control-plane-routes

## Summary

Implemented WP-05 only. The patch adds the FastAPI app factory, request dependencies, standard API error translation, and all documented WP-05 control-plane routes:

- `GET /health`
- `GET /health/dependencies`
- watcher create/list/read/patch/lifecycle/preview routes
- job list/detail/history/retry routes
- `GET /commands/{command_id}`
- `GET /events`
- `GET /metrics/summary`
- `GET /logs`
- `GET /files/browse`
- `POST /files/validate-path`
- `GET /config/dashboard-presentation`

All route request and response contracts use the existing WP-02 Pydantic API models. Repository-backed handlers use the existing WP-03 repositories. Event listing uses the WP-04 persisted outbox summary primitive and does not read Redis Streams directly from the API.

Watcher lifecycle and manual retry mutations persist command intent before returning `202`. Idempotency-key reuse is implemented for watcher lifecycle and retry commands through the WP-03 idempotency repository surface. The watcher routes compute and persist route preview metadata only; they do not start file polling or any later worker behavior.

The dashboard presentation route serves a requirement-backed embedded read-only fallback payload because the versioned YAML source file is not present in this repository slice and adding non-WP-05 config files was out of scope for this patch.

No new env vars, routes, schemas, event fields, metrics names, retries, worker loops, state transitions, tables, migrations, Streamlit pages, or Redis dashboard reads were added.

## Files Changed

- `requirements.txt`
- `requirements-dev.txt`
- `app/api/dependencies.py`
- `app/api/main.py`
- `app/api/errors.py`
- `app/api/routes/__init__.py`
- `app/api/routes/health.py`
- `app/api/routes/watchers.py`
- `app/api/routes/jobs.py`
- `app/api/routes/commands.py`
- `app/api/routes/events.py`
- `app/api/routes/metrics.py`
- `app/api/routes/files.py`
- `app/api/routes/config.py`
- `app/api/routes/operations.py`
- `tests/api/test_app_factory.py`
- `tests/api/test_health_routes.py`
- `tests/api/test_watcher_routes.py`
- `tests/api/test_job_routes.py`
- `tests/api/test_command_routes.py`
- `tests/api/test_event_routes.py`
- `tests/api/test_file_routes.py`
- `tests/api/test_metrics_log_config_routes.py`
- `tests/api/test_api_errors.py`
- `docs/worklogs/WORKLOG-20260501-wp05-fastapi-control-plane-routes.md`

## Requirements Affected

- `SL-API-001` through `SL-API-050`
- `SL-OBS-001` through `SL-OBS-012` where API route shaping, log summaries, and metrics summary are touched
- `SL-SEC-001` through `SL-SEC-017` where path allowlist and safe display-path behavior are touched
- `SL-FWM-020` through `SL-FWM-039` for watcher configuration and preview routes
- `SL-EVT-015`
- `SL-LIFE-015`
- `SL-RET-012`

## Contract/Schema Usage

- `docs/api/endpoints.md`
- `docs/schemas/api_schemas.md`
- `docs/reqs/REQ-010-fastapi-control-plane.md`
- `docs/reqs/REQ-011-streamlit-command-center.md`
- `docs/reqs/REQ-012-operational-logging-and-observability.md`
- `docs/reqs/REQ-013-security-and-path-safety.md`
- `app/api/schemas/api_models.py`
- `app/config/path_policy.py`
- `app/repositories/watchers.py`
- `app/repositories/jobs.py`
- `app/repositories/commands.py`
- `app/repositories/events.py`
- `app/repositories/observability.py`
- `app/events/outbox.py`

## Decisions Applied

- Added `fastapi` runtime dependency and `httpx` dev dependency only; no other dependency surface was changed.
- Used a shared FastAPI dependency layer for settings, sessions, path policy, correlation IDs, pagination, repository construction, filesystem browsing, and Redis readiness probing.
- Used the documented standard error envelope for `ApiError` and request-validation translation, including null field serialization.
- Implemented `GET /events` through `app.events.outbox.list_event_summaries(...)` so dashboard event listing stays on persisted metadata only.
- Implemented watcher route preview as tag-intersection computation only; no filesystem watcher start or worker action occurs inline.
- Persisted lifecycle and retry commands before returning `202` and reused the first accepted response when the same route scope and `Idempotency-Key` repeat.
- Used the documented embedded dashboard-presentation fallback because the YAML source file itself is absent and adding new non-WP-05 config artifacts was out of scope.
- Kept WP-06 and later work untouched.

## Verification Commands/Results

- `python -S tools/contract_lint.py --write-inventory`
  Result: passed
- `python tools/validate_schema_examples.py --write-evidence`
  Result: passed, `169` examples validated
- `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`
  Result: Sphinx build exit code `0`
- `pytest tests/contract`
  Result: `3 passed`
- `pytest tests/config tests/api tests/observability`
  Result: `47 passed`
- `pytest tests/schemas`
  Result: `213 passed`
- `pytest tests/db tests/repositories`
  Result: `9 passed`
- `pytest tests/events`
  Result: `8 passed`
- `pytest tests/api`
  Result: `33 passed`

## Assumptions

- Safe watcher-path request fields are treated as operator-safe display paths and are resolved against the configured source or destination allowlist roots before persistence when they are not already absolute allowlisted container paths.
- The summary metrics route returns bounded aggregate dictionaries from persisted state and does not parse Prometheus scrape output in WP-05.
- Command status responses expose `result_locator` through the generic `result` object only when a locator is present in persisted command metadata; WP-05 does not add later-stage command result schemas.

## Gaps

- The versioned dashboard presentation YAML file documented by `DEC-007` is still absent in this repository slice, so `GET /config/dashboard-presentation` serves the documented embedded fallback instead of resolved YAML content.
- The Windows test environment still emits pytest cache warnings and can leave restricted cache/temp directories behind. That is an environment artifact issue, not a failing verification gate, and cleanup was attempted again after verification.
- The metrics summary route uses persisted database aggregates only. No Prometheus scrape or WP-12 metrics middleware behavior was introduced here.

## Rollback Notes

- Revert `requirements.txt`, `requirements-dev.txt`, `app/api/`, `tests/api/`, and this worklog file.
- No migration rollback is required because WP-05 added no tables or schema changes.
- Demo/runtime cleanup after rollback is limited to deleting watcher, command, and log rows created during any manual API testing outside pytest.

## Next Step

WP-05 is complete from the API shell perspective. WP-06 can start watcher configuration execution, routing enforcement during detection, stability checks, and deduplication without changing the documented WP-05 API boundary.
