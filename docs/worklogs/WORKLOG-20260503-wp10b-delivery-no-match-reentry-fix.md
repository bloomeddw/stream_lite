# WORKLOG-20260503-wp10b-delivery-no-match-reentry-fix

## Summary

Fixed a WP10-B retry worker re-entry regression in the WP-09 delivery service no-match path.

The delivery service computed `delivery_start_state` so retry-released delivery jobs can preserve the correct previous state (`PROCESSED` for first delivery, `DELIVERING` for retry re-entry). The no-matching-destination branch did not pass that value into `_fail_without_delivery_targets`, causing the no-match delivery test to fail before the requirements-backed `NO_MATCHING_DESTINATION` transition could be recorded.

## Files changed

- `app/delivery/service.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260503-wp10b-delivery-no-match-reentry-fix.md`

## Requirements affected

- `SL-OUT-020`: zero matched destinations shall not enter delivery and shall record `NO_MATCHING_DESTINATION`.
- `SL-RET-018`: due retries shall re-enter only the failed eligible stage while preserving state history.

## Implementation notes

- Passed `delivery_start_state` into `_fail_without_delivery_targets` from the route-resolution no-target branch.
- No schema, migration, event payload, or repository changes were required.
- This path still avoids delivery claims, attempts, and outbox events for no-match jobs, matching the existing test and WP-09 contract.

## Verification

Run in review sandbox:

```text
python3 -m py_compile app/delivery/service.py
python3 -S tools/contract_lint.py --write-inventory
python3 tools/validate_schema_examples.py --write-evidence
```

Result: passed.

`pytest` could not run in the review sandbox because SQLAlchemy is not installed there. The failing project-environment test to rerun is:

```text
pytest tests/delivery/test_delivery_service.py::test_processed_job_without_matching_destination_transitions_to_failed_without_claim_or_events -q
```

Then rerun:

```text
pytest tests
```

## Assumptions

- No matching destination remains a pre-claim failure path.
- No matching destination should not enqueue `delivery.failed` because the event schema expects destination-specific details.

## Gaps

None known after this targeted fix.

## Rollback

Revert the one-line call-site change in `app/delivery/service.py` and remove this worklog/index entry.

## Next step

Apply the patch and rerun the failing delivery-service test plus the full suite.
