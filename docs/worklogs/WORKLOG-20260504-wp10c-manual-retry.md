# WORKLOG-20260504-wp10c-manual-retry

## Summary

- Implemented WP10-C manual retry command acceptance and execution handoff behind the existing `POST /jobs/{job_id}/retry` route.
- Added `ManualRetryService` to validate eligibility, persist the control command, create an immediate retry schedule, move `FAILED` jobs to `RETRY_PENDING`, append state history, and enqueue `retry.scheduled`.
- Kept worker execution out of scope; existing retry scheduler and processing/delivery workers remain responsible for actual re-entry execution.

## Requirements affected

- `SL-RET-006`
- `SL-RET-007`
- `SL-RET-008`
- `SL-RET-012`
- `SL-RET-020`
- `SL-API-005`
- `SL-API-037`
- `SL-LIFE-014`
- `SL-EVT-017`

## Files changed

- `app/retry/manual.py`
- `app/retry/__init__.py`
- `app/repositories/jobs.py`
- `app/api/routes/jobs.py`
- `tests/retry/test_manual_retry.py`
- `tests/api/test_job_routes.py`
- `docs/worklogs/INDEX.md`
- `docs/verification/evidence/sphinx_build.txt`

## Contract/schema usage

- Reused API contracts:
  - `schemas/api/retry_command_request.schema.json`
  - `schemas/api/command_accepted_response.schema.json`
  - `schemas/api/command_status_response.schema.json`
- Reused event contract:
  - `schemas/events/retry_scheduled.schema.json`
- Reused existing route and command idempotency scope:
  - `POST /jobs/{job_id}/retry`
  - `scope = job.retry:{job_id}`
- Reused existing command and retry persistence surfaces:
  - `CommandRepository`
  - `JobRepository`
  - `RetryRepository`
  - `EventOutboxRepository`

## Tests run

- `python -S tools/contract_lint.py --write-inventory`
  - passed
- `python tools/validate_schema_examples.py --write-evidence`
  - failed in the system interpreter: missing `jsonschema`
- `.\.venv\Scripts\python.exe tools/validate_schema_examples.py --write-evidence`
  - passed, `169` examples validated
- `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`
  - failed in the system interpreter: `sphinx-build` not found on `PATH`
- `$env:PATH="$PWD\.venv\Scripts;$env:PATH"; .\.venv\Scripts\python.exe tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`
  - passed, Sphinx exit code `0`
- `.\.venv\Scripts\pytest.exe tests/retry/test_manual_retry.py tests/api/test_job_routes.py -q`
  - passed, `19 passed`
- `.\.venv\Scripts\pytest.exe tests/retry -q`
  - passed, `38 passed`
- `.\.venv\Scripts\pytest.exe tests/api/test_job_routes.py -q`
  - passed, `7 passed`
- `.\.venv\Scripts\pytest.exe tests/processing -q`
  - passed, `13 passed`
- `.\.venv\Scripts\pytest.exe tests/delivery -q`
  - passed, `24 passed`
- `.\.venv\Scripts\pytest.exe tests/validation -q`
  - passed, `16 passed`
- `.\.venv\Scripts\pytest.exe tests/watcher -q`
  - passed, `11 passed`
- `.\.venv\Scripts\pytest.exe tests/events -q`
  - passed, `8 passed`
- `.\.venv\Scripts\pytest.exe tests/repositories -q`
  - passed, `6 passed`
- `.\.venv\Scripts\pytest.exe tests/config tests/api tests/observability -q`
  - passed, `55 passed`
- `.\.venv\Scripts\pytest.exe tests/schemas -q`
  - passed, `213 passed`
- `.\.venv\Scripts\pytest.exe tests/db -q`
  - passed, `3 passed`
- `.\.venv\Scripts\pytest.exe tests/contract -q`
  - passed, `3 passed`
- `.\.venv\Scripts\pytest.exe tests -q`
  - passed, `390 passed`

## Assumptions

- Manual retry creates an immediate retry schedule and leaves worker execution to existing processing/delivery workers.
- Dashboard controls remain part of WP-11.

## Gaps

- `CommandAcceptedResponse` does not expose retry metadata, so manual override visibility is carried through the command result locator and the internal `ManualRetryResult`, not the accepted `202` payload.
- The `retry.scheduled` event schema limits `retry_reason` to `256` characters; the full operator reason remains in the control command, while the event payload is bounded to the existing event contract.

## Rollback notes

- Revert the code and doc changes in this patch.
- No migration rollback is required.
- If this behavior is exercised against a durable environment outside tests, remove the corresponding `job.retry` command rows and `retry_schedules` rows, and move affected jobs out of `RETRY_PENDING` only through requirements-backed operational recovery.

## Next step

- WP-11 dashboard/manual retry controls can now target the existing retry route and poll command status without adding a new backend route.
