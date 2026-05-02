# WP-05 Codex Prompt: FastAPI App Shell and Control Plane Routes

Use this prompt only after WP-04 is complete and verified.

```text
You are continuing Stream Lite after WP-04.

Working directory:
C:\Users\asosa\stream_lite

Use the existing virtual environment in the working directory. Before running dependency-backed commands, activate it from PowerShell:
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

Do not vendor dependencies into `.pytest_vendor/`, `pytest_vendor/`, or `wheelhouse/`.

Start WP-05 only.

Work package:
WP-05 FastAPI App Shell and Control Plane Routes

Important:
- Do not start WP-06 or later.
- Do not create watcher polling, file detection, validation/quarantine workers, processing workers, delivery workers, retry scheduler loops, Streamlit pages, or new migrations.
- Do not restore REQ-018.
- Do not invent env vars, routes, schemas, event fields, metrics, retries, logs, state transitions, or tables.
- Implement only routes documented in docs/api/endpoints.md and mapped in docs/implementation/wp_reference/WP05_FASTAPI_CONTROL_PLANE_MAP.md.
- Follow `docs/implementation/wp_reference/WP05_LOW_REASONING_CHECKLIST.md` for fixed implementation order, route error rules, repository use, tests, and stop conditions.
- Use WP-02 Pydantic API models as request/response contracts.
- Use WP-03 repositories for persisted state.
- Use WP-04 event outbox/listing primitives where event handoff or event listing is required.
- Do not read Redis Streams directly from dashboard/API event listing routes.
- Every patch must include a worklog under docs/worklogs/.
- Do not include generated/cache/vendor artifacts: docs/_build/, .pytest_cache/, __pycache__/, *.pyc, .venv/, .pytest_vendor/, pytest_vendor/, wheelhouse/, .tmp/, pytest-cache-files-*.

Preflight:
1. Confirm WP-04 completion:
   - app/events/outbox.py exists.
   - app/events/dispatcher.py exists.
   - app/events/redis_streams.py exists.
   - tests/events pass locally.
   - docs/worklogs/WORKLOG-20260501-wp04-event-outbox-redis-streams-dispatcher.md or equivalent WP-04 worklog exists.

2. Run current verification before making WP-05 changes:
   python -S tools/contract_lint.py --write-inventory
   python tools/validate_schema_examples.py --write-evidence
   python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
   pytest tests/contract
   pytest tests/config tests/api tests/observability
   pytest tests/schemas
   pytest tests/db tests/repositories
   pytest tests/events

3. Remove docs/_build/ again after Sphinx verification before continuing.

Read before changing files:
- docs/implementation/CODEX_TASK_GUIDE.md
- docs/implementation/wp_reference/WP05_FASTAPI_CONTROL_PLANE_MAP.md
- docs/implementation/wp_reference/WP05_LOW_REASONING_CHECKLIST.md
- docs/implementation/naming_review.md
- docs/api/endpoints.md
- docs/schemas/api_schemas.md
- docs/reqs/REQ-010-fastapi-control-plane.md
- docs/reqs/REQ-012-operational-logging-and-observability.md
- docs/reqs/REQ-013-security-and-path-safety.md
- app/api/schemas/api_models.py
- app/api/errors.py
- app/config/settings.py
- app/config/path_policy.py
- app/db/session.py
- app/repositories/*.py
- app/events/outbox.py
- app/events/dispatcher.py
- app/events/redis_streams.py

WP-05 requirement IDs:
- SL-API-001 through SL-API-050
- SL-OBS-001 through SL-OBS-012 where API logs/metrics are touched
- SL-SEC-001 through SL-SEC-017 where path safety is touched
- SL-FWM-020 through SL-FWM-039 for watcher config and route preview routes
- SL-EVT-015 and SL-API-032 for event listing
- SL-LIFE-015 and SL-API-047 for command status
- SL-RET-012 and SL-API-046 for retry command acceptance

Target files/modules:
Create or update only WP-05 files:
- app/api/main.py
- app/api/dependencies.py
- app/api/routes/__init__.py
- app/api/routes/health.py
- app/api/routes/watchers.py
- app/api/routes/jobs.py
- app/api/routes/commands.py
- app/api/routes/events.py
- app/api/routes/metrics.py
- app/api/routes/files.py
- app/api/routes/config.py
- app/api/routes/operations.py
- app/api/errors.py only for route-compatible error response helpers if needed
- tests/api/test_app_factory.py
- tests/api/test_health_routes.py
- tests/api/test_watcher_routes.py
- tests/api/test_job_routes.py
- tests/api/test_command_routes.py
- tests/api/test_event_routes.py
- tests/api/test_file_routes.py
- tests/api/test_metrics_log_config_routes.py
- tests/api/test_api_errors.py
- docs/worklogs/WORKLOG-<date>-wp05-fastapi-control-plane-routes.md

Use this fixed route implementation map:
- GET /health -> HealthResponse, no dependency probe.
- GET /health/dependencies -> DependencyHealthResponse, check DB, Redis readiness if WP-04 exposes it, and filesystem roots.
- POST /watchers -> WatcherCreateRequest to WatcherDetailResponse, persist watcher config/sources/destinations/route preview, no file polling.
- GET /watchers -> WatcherListResponse with pagination.
- GET /watchers/{watcher_id} -> WatcherDetailResponse or WATCHER_NOT_FOUND.
- PATCH /watchers/{watcher_id} -> WatcherPatchRequest to WatcherDetailResponse; reject empty body with EMPTY_PATCH.
- POST /watchers/{watcher_id}/start|pause|resume|stop -> LifecycleCommandRequest to CommandAcceptedResponse; persist command intent before 202, no inline watcher work.
- POST /watchers/{watcher_id}/preview-routes -> RoutePreviewRequest to RoutePreviewResponse; compute only, no job creation.
- GET /jobs -> JobListResponse with filters and deterministic ordering.
- GET /jobs/{job_id} -> JobDetailResponse.
- GET /jobs/{job_id}/history -> JobHistoryResponse.
- POST /jobs/{job_id}/retry -> RetryCommandRequest to CommandAcceptedResponse; persist command intent only.
- GET /commands/{command_id} -> CommandStatusResponse.
- GET /events -> EventListResponse from persisted event metadata; never read Redis directly.
- GET /metrics/summary -> MetricsSummaryResponse.
- GET /logs -> OperationalLogListResponse.
- GET /files/browse -> FolderBrowseResponse constrained to allowlisted roots.
- POST /files/validate-path -> PathValidationRequest to PathValidationResponse using WP-01 path policy.
- GET /config/dashboard-presentation -> DashboardPresentationResponse.

Shared behavior to implement:
- Generate or propagate correlation_id for every response.
- Standard error responses SHALL include error_code, message, field, resource_id, current_state, and correlation_id.
- Pagination default limit=50, max=500, offset>=0.
- Invalid pagination returns 422 PAGINATION_INVALID.
- Invalid filters return 422 FILTER_INVALID.
- Command routes accept missing Idempotency-Key but reuse command response when the same supplied Idempotency-Key/scope repeats.
- Mutation command routes return 202 only after command record persistence.
- Event listing returns API-safe summaries only; no raw payload_json in response.
- Structured logs must not include secrets or unsafe host paths.

Allowed dependency changes:
- Add fastapi>=0.110,<1 to requirements.txt if not already present.
- Add httpx>=0.27,<1 to requirements-dev.txt if needed for route tests.
- Add uvicorn only if a local server entrypoint is introduced; route tests do not require uvicorn.
- Do not add new env vars.

Verification commands to run from C:\Users\asosa\stream_lite:
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/contract
pytest tests/config tests/api tests/observability
pytest tests/schemas
pytest tests/db tests/repositories
pytest tests/events
pytest tests/api

After verification:
- Remove docs/_build/ again before final handoff.
- Remove generated/cache/vendor artifacts: docs/_build/, .pytest_cache/, __pycache__/, *.pyc, .venv/, .pytest_vendor/, pytest_vendor/, wheelhouse/, .tmp/, pytest-cache-files-*.
- Keep evidence files current.
- Add a WP-05 worklog.

WP-05 completion criteria:
- FastAPI app factory exists.
- All routes listed in docs/api/endpoints.md are implemented or have a requirement-backed documented deferral.
- Route request/response models use WP-02 Pydantic models.
- Repository-backed routes use WP-03 repositories.
- Event listing uses WP-04 safe event listing/outbox metadata and never reads Redis directly.
- Command mutation routes persist command intent before returning 202.
- Standard errors include all fields and correlation_id.
- API route tests pass.
- Existing WP-00 through WP-04 tests still pass.
- No generated/cache/vendor artifacts are included.
- WP-06 is not started.

Expected response:
1. Scope
2. Preflight result
3. Requirements implemented
4. Files changed
5. API route summary
6. Tests run
7. Evidence artifacts
8. Rollback notes
9. Gaps
10. Final verdict: ready or not ready for WP-06
```
