# WORKLOG-20260503-wp10b-retry-scheduler

## Summary

Implemented WP10-B automatic retry scheduling and due-retry release only: persisted retry schedules, moved retryable jobs into `RETRY_PENDING`, reset due retries back to the eligible failed stage, finalized exhausted and non-retryable failures, and emitted `retry.scheduled` / `job.failed` outbox events.

## Requirements affected

- `SL-RET-006`
- `SL-RET-007`
- `SL-RET-008`
- `SL-RET-009`
- `SL-RET-010`
- `SL-RET-011`
- `SL-RET-013`
- `SL-RET-014`
- `SL-RET-018`
- `SL-RET-019`
- `SL-JOB-043`
- `SL-LIFE-010`
- `SL-LIFE-014`
- `SL-EVT-022`
- `SL-EVT-023`

## Files changed

- `app/retry/__init__.py`
- `app/retry/scheduler.py`
- `app/repositories/retry.py`
- `tests/retry/test_scheduler.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260503-wp10b-retry-scheduler.md`
- `docs/verification/evidence/schema_fixture_validation.md`
- `docs/verification/evidence/sphinx_build.txt`

## Decisions applied

- Reused the existing job lifecycle transitions and only added retry-repository helpers that do not require a migration.
- Kept retry scheduling stage-local: only validation, processing, and delivery are persisted as retry schedules because those are the retry stages backed by the current table contract.
- Marked anomalous due schedules as `failed` when the job is missing or no longer in a valid retry state so restart reconciliation does not loop forever on the same row.
- Kept due-retry release side-effect free: state reset and retry status updates only, with no processing, delivery, or validation worker execution.

## Tests or verification commands run

```bash
python -S tools/contract_lint.py --write-inventory
```

Result: passed.

```bash
python tools/validate_schema_examples.py --write-evidence
```

Result: failed in the host interpreter because `jsonschema` was unavailable.

```bash
.\.venv\Scripts\python.exe tools/validate_schema_examples.py --write-evidence
```

Result: passed; `169` examples validated and `169` passed.

```bash
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
```

Result: skipped in the host environment because `sphinx-build` was not on `PATH`.

```bash
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"; python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
```

Result: passed; Sphinx HTML build exit code `0`.

```bash
.\.venv\Scripts\pytest.exe tests/retry/test_scheduler.py -q
```

Result: passed; `11` tests passed.

```bash
.\.venv\Scripts\pytest.exe tests/retry -q
```

Result: passed; `26` tests passed.

```bash
.\.venv\Scripts\pytest.exe tests/processing -q
```

Result: failed inside the sandbox because pytest could not access the Windows temp root used by `tmp_path`.

```bash
.\.venv\Scripts\pytest.exe tests/processing -q
```

Result: passed after rerunning outside the sandbox; `12` tests passed.

```bash
.\.venv\Scripts\pytest.exe tests/delivery -q
```

Result: passed outside the sandbox; `23` tests passed.

```bash
.\.venv\Scripts\pytest.exe tests/validation -q
```

Result: passed outside the sandbox; `16` tests passed.

```bash
.\.venv\Scripts\pytest.exe tests/watcher -q
```

Result: passed outside the sandbox; `11` tests passed.

```bash
.\.venv\Scripts\pytest.exe tests/events -q
```

Result: passed; `8` tests passed. Pytest emitted a cache-path warning for `.pytest_cache`.

```bash
.\.venv\Scripts\pytest.exe tests/repositories -q
```

Result: passed; `6` tests passed. Pytest emitted a cache-path warning for `.pytest_cache`.

```bash
.\.venv\Scripts\pytest.exe tests/config tests/api tests/observability -q
```

Result: passed; `55` tests passed. Pytest emitted a cache-path warning for `.pytest_cache`.

```bash
.\.venv\Scripts\pytest.exe tests/schemas -q
```

Result: passed; `213` tests passed. Pytest emitted a cache-path warning for `.pytest_cache`.

```bash
.\.venv\Scripts\pytest.exe tests/db -q
```

Result: failed inside the sandbox because pytest could not access the Windows temp root used by `tmp_path`.

```bash
.\.venv\Scripts\pytest.exe tests/db -q
```

Result: passed after rerunning outside the sandbox; `3` tests passed.

```bash
.\.venv\Scripts\pytest.exe tests/contract -q
```

Result: passed; `3` tests passed. Pytest emitted a cache-path warning for `.pytest_cache`.

```bash
.\.venv\Scripts\pytest.exe tests -q
```

Result: passed after rerunning outside the sandbox; `376` tests passed.

## Assumptions

- Retry scheduling is invoked after the stage-local failure has already been persisted, so validation failures reach the scheduler from `INVALID` when they need a valid transition to `QUARANTINED`.
- Event-stage broker retry remains owned by the outbox/dispatcher surfaces and is not persisted in `retry_schedules` because the current retry table only supports validation, processing, and delivery stages.

## Gaps

- Manual retry command acceptance and execution remain out of scope for WP10-B.
- No new `job.state_changed` emission was added in this slice because the task contract limited WP10-B event work to `retry.scheduled` and `job.failed`.

## Rollback notes

Revert the files listed above to remove the scheduler surface, repository helpers, tests, worklog, and updated evidence. No migration rollback is required because WP10-B reused the existing retry schedule table.

## Next step

WP10-B is ready for WP10-C manual retry acceptance/execution work on top of the persisted scheduler surface.
