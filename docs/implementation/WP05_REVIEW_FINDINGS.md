# WP-05 Review Findings and Cleanup Scope

## Review status

WP-05 is **functionally close but not cleanly closed**. The route shell, route modules, command intent persistence, repository-backed reads, and persisted event listing are present. The current repository state should not be treated as ready for WP-06 until the cleanup items below are resolved or explicitly deferred with requirements-backed rationale.

## Sources reviewed

- `docs/implementation/WP05_CODEX_PROMPT.md`
- `docs/implementation/wp_reference/WP05_FASTAPI_CONTROL_PLANE_MAP.md`
- `docs/implementation/wp_reference/WP05_LOW_REASONING_CHECKLIST.md`
- `docs/api/endpoints.md`
- `docs/reqs/REQ-010-fastapi-control-plane.md`
- `docs/reqs/REQ-012-operational-logging-and-observability.md`
- `docs/reqs/REQ-013-security-and-path-safety.md`
- `docs/schemas/api_schemas.md`
- `docs/verification/verification_matrix.md`
- `docs/worklogs/WORKLOG-20260501-wp05-fastapi-control-plane-routes.md`
- `app/api/**`
- `tests/api/**`
- `rtc_source.md`

## Positive findings

- `app/api/main.py` defines a FastAPI app factory and registers route modules.
- WP-05 routes are present for health, watcher configuration/lifecycle, jobs, commands, events, metrics summary, logs, files, and dashboard presentation.
- Route handlers use the WP-02 Pydantic models rather than ad hoc response dictionaries for the main contracts.
- Repository-backed routes use WP-03 repositories.
- `GET /events` uses `app.events.outbox.list_event_summaries(...)` and does not read Redis Streams directly.
- Watcher lifecycle commands and job retry commands persist command records before returning `202`.
- The uploaded repository no longer contains `__pycache__`, `.pytest_cache`, `.tmp`, `tmp`, `.venv`, `wheelhouse`, or pyc artifacts.

## Blocking cleanup findings

### F-WP05-001 - Sphinx/index references point to moved WP-05 reference files

`docs/index.rst`, `docs/implementation/README.md`, `docs/implementation/CODEX_TASK_GUIDE.md`, `docs/implementation/WP05_CODEX_PROMPT.md`, and the WP-05 reference map referenced `docs/implementation/WP05_FASTAPI_CONTROL_PLANE_MAP.md` and `docs/implementation/WP05_LOW_REASONING_CHECKLIST.md`, but the repository stores those files under `docs/implementation/wp_reference/`.

This patch corrects those documentation paths so Sphinx and future prompts use the actual checked-in references.

### F-WP05-002 - Route observability is not implemented for the documented API contract

The endpoint matrix and `SL-API-041` through `SL-API-050` require route log events and `stream_lite_api_request_duration_seconds` or related metrics. The implementation defines `emit_api_route_log(...)`, but the helper is not called by the route handlers. There is also no request metrics middleware or tested metrics sink in WP-05.

Required cleanup:

- Add a minimal FastAPI middleware or dependency-backed wrapper that records request duration for every documented route.
- Emit the documented route log event for successful and failed route handling, without secrets or unsafe host paths.
- Add route tests proving at least one read route, one mutation route, and one error path create sanitized operational log rows or route log records as required.
- If route metrics/logging are intentionally deferred to WP-12, add an explicit requirements-backed deferral and update `REQ-010`, `REQ-012`, `docs/api/endpoints.md`, and verification rows in the same patch.

### F-WP05-003 - Dependency health requirement and schema/code disagree on `error_code`

`REQ-010` says each dependency health entry includes `name`, `status`, `checked_at`, and optional `error_code`, but `schemas/api/dependency_health_response.schema.json`, `DependencyHealthItem`, and `app/api/routes/health.py` omit `error_code`.

Required cleanup:

- Either add nullable `error_code` to the schema, Pydantic model, examples, and health route, or revise the requirement to remove `error_code` from dependency items.
- Prefer adding the field because `DependencyProbeResult` already captures `error_code`.
- Update schema examples and `tests/api/test_health_routes.py`.

### F-WP05-004 - Lifecycle state wording is inconsistent for pause/stop

`REQ-010` endpoint details mention an `idle` watcher state for pause/stop, but the active `WatcherLifecycleState` schema uses `CREATED`, `ACTIVE`, `PAUSED`, `STOPPING`, `STOPPED`, and `ERROR`. The implementation allows pause only from `ACTIVE` and stop from `CREATED`, `ACTIVE`, `PAUSED`, and `ERROR`.

Required cleanup:

- Normalize the requirement wording to active schema states, or add an explicit `IDLE` state everywhere if it is still required.
- Update tests for the chosen contract.

### F-WP05-005 - Idempotency-key replay does not check payload hash compatibility

Lifecycle and retry command routes reuse the first response for the same route scope and `Idempotency-Key`. The stored payload hash is not checked before replay. `SL-API-037` says duplicate keys for the same resource and payload return the original command response, which implies a same-key/different-payload case must be handled explicitly.

Required cleanup:

- Add repository support or route-side logic to reject same-scope same-key different-payload requests with a stable conflict error.
- Add tests for identical-payload replay and mismatched-payload rejection.

### F-WP05-006 - `/files/browse` invalid-purpose error code is not aligned

`REQ-010` lists `PURPOSE_INVALID` for invalid browse purpose in one endpoint table. The implementation returns `REQUEST_VALIDATION_FAILED`, and `docs/api/endpoints.md` does not list `PURPOSE_INVALID` for the same route.

Required cleanup:

- Choose one error code and align `REQ-010`, `docs/api/endpoints.md`, route code, tests, and verification matrix.
- Prefer `PURPOSE_INVALID` if the purpose query remains a domain-specific validation rule.

### F-WP05-007 - `app/api/__init__.py` has stale WP-01 wording

The module docstring says `Shared API error primitives for WP-01`, but the package now owns the WP-05 FastAPI control-plane API shell. This is not blocking by itself, but it should be cleaned while the WP-05 files are already being touched.

## Verification attempted during review

- `python -S tools/contract_lint.py --write-inventory`: passed.
- Dependency-backed verification commands could not be rerun reliably in this sandbox because the active `/opt/pyvenv/bin/python` process hangs on normal site-package startup and the base `/usr/bin/python3` environment does not include project dependencies such as SQLAlchemy/jsonschema. Treat the Codex-reported WP-05 test output in the worklog as unverified by this review until rerun in the project virtual environment.

## Required cleanup evidence

A cleanup patch should provide:

- passing `python -S tools/contract_lint.py --write-inventory`
- passing `python tools/validate_schema_examples.py --write-evidence`
- passing Sphinx verification with no missing toctree references
- passing `pytest tests/api tests/contract tests/config tests/observability tests/schemas tests/db tests/repositories tests/events`
- updated `docs/verification/evidence/*`
- a new `docs/worklogs/WORKLOG-<date>-wp05-cleanup-verification.md`

## WP-06 readiness verdict

Not ready. Start WP-06 only after the blocking cleanup findings are fixed or requirements-backed deferrals are documented and verified.
