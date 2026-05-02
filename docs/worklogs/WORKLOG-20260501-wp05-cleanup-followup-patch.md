# WORKLOG-20260501-wp05-cleanup-followup-patch

## Summary

Reviewed the post-WP-05 cleanup repository and found that several cleanup findings remained unimplemented. Added a follow-up patch to close the remaining WP-05 cleanup gaps without starting WP-06 or adding new environment variables, migrations, worker loops, Streamlit pages, or generated artifacts.

## Files changed

- `app/api/main.py`
- `app/api/errors.py`
- `app/api/__init__.py`
- `app/api/routes/files.py`
- `app/api/routes/health.py`
- `app/api/routes/jobs.py`
- `app/api/routes/watchers.py`
- `app/api/schemas/api_models.py`
- `docs/api/endpoints.md`
- `docs/reqs/REQ-010-fastapi-control-plane.md`
- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260501-wp05-cleanup-followup-patch.md`
- `schemas/api/dependency_health_response.schema.json`
- `schemas/examples/api/dependency_health_response.*.json`
- `tests/api/test_file_routes.py`
- `tests/api/test_health_routes.py`
- `tests/api/test_job_routes.py`
- `tests/api/test_route_observability.py`
- `tests/api/test_watcher_routes.py`

## Requirements affected

- `SL-API-001`
- `SL-API-002`
- `SL-API-003`
- `SL-API-004`
- `SL-API-005`
- `SL-API-013`
- `SL-API-014`
- `SL-API-039`
- `SL-API-041` through route observability coverage
- `SL-OBS-005`
- `SL-OBS-008`
- `SL-OBS-010`
- `SL-SEC-001`
- `SL-LIFE-015`

## Decisions applied

No new design decisions were introduced. The patch follows the existing WP-05 review recommendation to keep cleanup limited to route observability, dependency-health contract alignment, idempotency replay safety, domain error-code alignment, stale docstring cleanup, tests, and docs.

## Tests and verification

Executed in the review sandbox:

```bash
python -S tools/contract_lint.py --write-inventory
```

Result: passed.

Additional full verification commands from the WP-05 cleanup prompt were not run in this sandbox because the available base Python environment lacked the project test dependencies (`jsonschema`, `pytest`, `pydantic`, `fastapi`, `sqlalchemy`, and `sphinx`), and dependency installation did not complete in the sandbox. Codex should run the full required suite in the project virtual environment before accepting this patch.

Static syntax validation was run with `ast.parse` across project Python files and passed.

## Assumptions

- In-memory `app.state.api_request_observations` is acceptable as the WP-05 route-duration recording surface until the later Prometheus integration work package wires a production scrape endpoint.
- Route middleware may emit route-level structured logs using the documented endpoint event names rather than duplicating route-specific log calls in every handler.
- `IDEMPOTENCY_KEY_CONFLICT` is the stable conflict code for a same-scope, same-key request whose payload hash differs from the first accepted payload.
- `PURPOSE_INVALID` is the active domain error for invalid `/files/browse` purpose values.

## Gaps

- Full pytest, schema example validation, and Sphinx verification still need to run in the developer environment with `requirements-dev.txt` installed.
- This patch does not implement the future Prometheus exporter; it only records request observations in process and emits structured logs for WP-05 route coverage.

## Rollback notes

Revert the files listed above to return to the prior WP-05 cleanup state. No migrations, environment variables, or persisted schema changes beyond JSON schema/example files were added.

## Next step

Apply this patch, run the full WP-05 cleanup verification suite, and only then start WP-06 from `docs/implementation/wp_reference/WP06_WATCHER_REFERENCE.md` if all checks pass.
