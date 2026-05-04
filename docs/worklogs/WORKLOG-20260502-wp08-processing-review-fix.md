# WORKLOG-20260502-wp08-processing-review-fix

## Summary

Reviewed the WP-08 processing worker implementation against the WP-08 reference map and active requirements. The review found that the worker accepted `VALIDATED` state without confirming a successful validation attempt, and that the output manifest artifact did not yet carry all processing-owned timing/version/output locator fields required by `SL-PRO-DATA-001`. This patch closes those gaps and moves processing tests to pytest-managed temporary directories so tests do not create repo-local scratch folders.

## Requirements affected

- `SL-PRO-015`
- `SL-PRO-016`
- `SL-PRO-017`
- `SL-PRO-026`
- `SL-PRO-DATA-001`
- `SL-DCT-009`
- `SL-DCT-010`
- `SL-DCT-011`
- `SL-DCT-029`
- `SL-SEC-013`

## Files changed

- `app/processing/engine.py`
- `app/processing/spark_adapter.py`
- `app/artifacts/models.py`
- `schemas/artifacts/output_manifest.schema.json`
- `schemas/examples/artifacts/output_manifest.valid.json`
- `schemas/examples/artifacts/output_manifest.invalid_enum.json`
- `docs/schemas/artifact_schemas.md`
- `tests/processing/test_spark_adapter.py`
- `tests/processing/test_processing_worker.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260502-wp08-processing-review-fix.md`

## Implementation notes

- `ProcessingWorker` now depends on `ValidationRepository` and skips processing when a `VALIDATED` job lacks a latest successful validation attempt.
- The skip path emits a structured `processing.validation_not_confirmed` log and performs no stage claim, processing attempt, adapter call, state transition, or event enqueue.
- `OutputManifest` now includes `processor_version`, `produced_output_locators`, `started_at`, `completed_at`, and `duration_seconds` so the artifact carries processing-owned version, timing, duration, and produced output locator data.
- `SparkDemoAdapter` writes the expanded output manifest payload and still validates it before returning a successful processing result.
- Processing tests use `tmp_path` rather than repo-local `tmp_processing_tests` scratch directories.

## Tests / verification

Executed in the review sandbox:

```bash
python -m py_compile app/processing/engine.py app/processing/spark_adapter.py app/artifacts/models.py tests/processing/test_spark_adapter.py tests/processing/test_processing_worker.py
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python - <<'PY'
import json
from app.artifacts import OutputManifest
payload = json.load(open('schemas/examples/artifacts/output_manifest.valid.json'))
print(OutputManifest.model_validate(payload).status)
PY
```

Results: all commands passed. Full pytest and Sphinx verification must be rerun in the project virtual environment because the review sandbox does not include SQLAlchemy/Sphinx project dependencies.

## Assumptions

- A successful validation attempt is required for WP-08 processing even when a job row is already in `VALIDATED` state.
- The output manifest artifact schema may be expanded in WP-08 without a database migration because the existing output manifest table already stores produced output locators and processing summary locator separately from the artifact JSON file.
- Delivery remains out of scope; `destination_outcomes=[]` and `status=processed` remain valid pre-delivery values.

## Gaps

- Full dependency-backed pytest and Sphinx runs are deferred to the user/Codex environment.
- Worker event-bus consumption loops, processing concurrency configuration, graceful shutdown, and live Spark/Flink runtime execution remain out of the current callable WP-08 scope.

## Rollback notes

Revert the files listed above to remove the validation-attempt guard and expanded output manifest artifact fields. No database migration rollback is required for this patch.

## Next step

Rerun the full WP-08 verification suite. If it passes, WP-08 can hand off to WP-09 delivery work.
