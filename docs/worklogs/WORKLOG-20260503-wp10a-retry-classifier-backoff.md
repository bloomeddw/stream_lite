# WORKLOG-20260503-wp10a-retry-classifier-backoff

## Summary

Implemented WP10-A retry primitives only: a stage-aware retry classifier and a configurable backoff policy built from the existing retry settings surface.

## Requirements affected

- `SL-RET-001`
- `SL-RET-004`
- `SL-RET-005`
- `SL-RET-010`
- `SL-RET-016`
- `SL-RET-017`
- `SL-JOB-043`

## Files changed

- `app/retry/__init__.py`
- `app/retry/classifier.py`
- `app/retry/backoff.py`
- `tests/retry/test_classifier.py`
- `tests/retry/test_backoff.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260503-wp10a-retry-classifier-backoff.md`
- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`

## Decisions applied

- Reused the existing retry failure-class contract of `retryable` and `non_retryable`.
- Kept validation-policy and path/security failures non-retryable by default.
- Split backoff delay calculation from retry-attempt eligibility so max-attempt checks stay explicit.

## Tests or verification commands run

```bash
python -S tools/contract_lint.py --write-inventory
```

Result: passed.

Requested host-shell commands and observed environment issues:

```bash
python tools/validate_schema_examples.py --write-evidence
```

Result: failed under the host `python` because `jsonschema` was not available to that interpreter.

```bash
pytest tests/retry/test_classifier.py tests/retry/test_backoff.py
```

Result: failed in the host shell because `pytest` was not on `PATH`.

Project-environment reruns:

```bash
.\.venv\Scripts\python.exe tools/validate_schema_examples.py --write-evidence
```

Result: passed; `169` examples validated and `169` passed.

```bash
.\.venv\Scripts\pytest.exe tests/retry/test_classifier.py tests/retry/test_backoff.py
```

Result: passed; `10` tests passed. Pytest emitted one cache-path warning because it could not create `.pytest_cache` in this workspace.

## Assumptions

- Existing processing and delivery repo-local failure codes should map onto the retry policy even when the requirement tables list a more generic transient code catalog.
- Jitter bounds are not numerically specified in the retry requirements, so this slice uses a bounded multiplicative jitter window for deterministic testing and later scheduler reuse.

## Gaps

- `app/retry/scheduler.py` remains out of scope.
- Manual retry execution remains out of scope.
- Retry event enqueueing and terminal-state transitions remain out of scope.
- The host-shell `python` and `pytest` entrypoints are not aligned with the repo virtualenv, so verification currently depends on `.venv`.

## Rollback notes

Revert the files listed above to remove the WP10-A primitive surfaces. No migration rollback or data cleanup is required.

## Next step

Build WP10-B on top of these primitives by persisting retry schedules, moving jobs into and out of `RETRY_PENDING`, and emitting `retry.scheduled` and `job.failed`.
