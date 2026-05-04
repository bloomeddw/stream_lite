# WORKLOG-20260503-wp10b-retry-worker-reentry-closure

## Summary

Closed a WP10-B integration gap found during post-test review: due retry release moved jobs from `RETRY_PENDING` back to the failed stage state (`PROCESSING` or `DELIVERING`), but the processing and delivery workers still only accepted pre-stage source states (`VALIDATED` and `PROCESSED`). This patch allows retry-released jobs with retry attempt numbers to be picked up by the existing workers without running retry business logic inside the scheduler.

## Requirements affected

- `SL-RET-006`
- `SL-RET-007`
- `SL-RET-008`
- `SL-RET-018`
- `SL-LIFE-010`
- `SL-LIFE-014`

## Files changed

- `app/processing/engine.py`
- `app/delivery/service.py`
- `tests/processing/test_processing_worker.py`
- `tests/delivery/test_delivery_service.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260503-wp10b-retry-worker-reentry-closure.md`

## Implementation notes

- `ProcessingWorker` now treats `PROCESSING` jobs with `attempt_number > 1` as retry-released processable work.
- `DeliveryWorker` now treats `DELIVERING` jobs with `attempt_number > 1` as retry-released deliverable work.
- Batch claim helpers include retry-released in-stage jobs in addition to normal pre-stage jobs.
- Retry scheduler behavior remains unchanged: it does not execute validation, processing, or delivery business logic.
- The normal first-attempt entry contracts remain unchanged: processing still starts from `VALIDATED`, and delivery still starts from `PROCESSED`.

## Tests run

```bash
python -m py_compile app/retry/*.py app/processing/engine.py app/delivery/service.py tests/retry/*.py tests/processing/test_processing_worker.py tests/delivery/test_delivery_service.py
```

Result: passed.

```bash
python -S tools/contract_lint.py --write-inventory
```

Result: passed.

```bash
python tools/validate_schema_examples.py --write-evidence
```

Result: passed; `169` examples validated and `169` passed.

Full pytest was not run in this sandbox because the repository test dependencies are not installed here. The project environment should rerun `pytest tests/retry -q`, `pytest tests/processing -q`, `pytest tests/delivery -q`, and `pytest tests` after applying the patch.

## Assumptions

- Retry-released in-stage jobs have `attempt_number > 1`; first attempts continue to enter workers through the existing pre-stage states.
- Existing stage claim protection remains the duplicate-execution guard for retry-released in-stage work.

## Gaps

- Manual retry command acceptance and execution remain out of scope for WP10-B.

## Rollback notes

Revert the files listed above to return worker eligibility to pre-stage states only. No migration or schema rollback is required.

## Next step

Rerun the full verification suite. If it passes, continue with WP10-C manual retry command acceptance/execution.
