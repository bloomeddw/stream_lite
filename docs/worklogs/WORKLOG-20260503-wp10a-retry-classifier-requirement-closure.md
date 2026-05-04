# WORKLOG-20260503-wp10a-retry-classifier-requirement-closure

## Summary

Closed a WP10-A retry classification gap found during requirements review. The classifier now covers event/broker failures from the active retry requirements and retry policy, including `BROKER_UNAVAILABLE` and `BROKER_PUBLISH_FAILURE`.

## Requirements affected

- `SL-RET-001`
- `SL-RET-010`
- `SL-RET-016`
- `SL-EVT-017`
- `SL-EVT-022`
- `SL-EVT-023`

## Files changed

- `app/retry/classifier.py`
- `tests/retry/test_classifier.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260503-wp10a-retry-classifier-requirement-closure.md`

## Implementation notes

- Added `event` as a retry classification stage for event publication/consumption failures.
- Added `broker` as an accepted input alias that normalizes to `event` so future scheduler/outbox integrations can use either vocabulary safely.
- Kept path-policy failures non-retryable for event handling.
- Did not implement scheduler, manual retry, state transitions, or event enqueueing; those remain WP10-B or later scope.

## Tests run

```bash
python3 -m py_compile app/retry/classifier.py tests/retry/test_classifier.py
python3 -S tools/contract_lint.py --write-inventory
python3 tools/validate_schema_examples.py --write-evidence
```

Result: passed in the review sandbox.

## Assumptions

- Event publication and broker retry vocabulary should share the same classifier owner stage, normalized as `event`.
- `BROKER_PUBLISH_FAILURE` from the operations retry policy is an alias-like retryable broker publication condition alongside `BROKER_UNAVAILABLE` from REQ-009.

## Gaps

- Scheduler persistence, due retry execution, exhausted retry finalization, and manual retry remain out of scope for WP10-A.

## Rollback notes

Revert the files listed above to remove the event/broker retry classifier closure. No migration or data rollback is required.

## Next step

Proceed to WP10-B retry scheduler persistence and event integration after the full project test suite passes.
