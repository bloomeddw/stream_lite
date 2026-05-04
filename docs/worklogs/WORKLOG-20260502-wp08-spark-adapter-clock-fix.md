# WORKLOG-20260502-wp08-spark-adapter-clock-fix

## Summary
Fixed a WP-08 processing adapter timestamp regression found by `tests/processing/test_spark_adapter.py::test_csv_input_preserves_rows_and_writes_valid_artifacts`.

## Files Changed
- `app/processing/spark_adapter.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260502-wp08-spark-adapter-clock-fix.md`

## Requirements Affected
- `REQ-007` / WP-08 processing artifact creation and processing duration reporting.
- `REQ-016` / artifact contract consistency for processing summary and output manifest timestamps.

## Issue
`SparkDemoAdapter.run_demo_transform()` called the injectable clock once before processing and again after processing. Deterministic WP-08 tests expected the first post-start clock tick to represent completion, so the output manifest `completed_at` advanced to `2026-05-02T14:00:02Z` instead of `2026-05-02T14:00:01Z`.

## Change
Removed the eager pre-processing clock call. Failure paths now call the clock only when producing a failure result. Successful processing now calls the clock once after the transform and uses that timestamp consistently for the processing summary, output manifest, and adapter result.

## Verification
Run in sandbox:
- `python -m py_compile app/processing/spark_adapter.py`

Not run in sandbox due to missing project dependencies:
- `pytest tests/processing -q`
- `pytest tests`

## Assumptions
The deterministic clock in tests represents completion when first called after the supplied `started_at`.

## Gaps
None known.

## Rollback Notes
Revert `app/processing/spark_adapter.py` and this worklog/index entry if this timestamp behavior must be undone.

## Next Step
Rerun full WP-08 verification in the project virtual environment.
