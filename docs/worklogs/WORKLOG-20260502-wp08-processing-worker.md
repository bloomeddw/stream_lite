# WORKLOG-20260502-wp08-processing-worker

## Summary

Implemented WP-08 processing as a callable worker slice. The patch adds a deterministic Spark-profile demo adapter, processing-stage claim/orchestration, durable `processing_summary.json` and pre-delivery `output_manifest.json` creation, output-manifest persistence, processing lifecycle events, and focused processing tests without starting delivery or retry scheduling.

## Requirements affected

- `SL-PRO-001` through `SL-PRO-017`
- `SL-PRO-020`
- `SL-PRO-024` through `SL-PRO-029`
- `SL-PRO-DATA-001`
- `SL-JOB-040`
- `SL-OBS-024`
- `SL-SEC-013`
- `SL-SEC-014`
- `SL-DCT-009`
- `SL-DCT-010`
- `SL-DCT-011`
- `SL-DCT-022`
- `SL-DCT-023`
- `SL-DCT-029`
- `SL-DCT-032`

## Files changed

- `app/processing/__init__.py`
- `app/processing/engine.py`
- `app/processing/spark_adapter.py`
- `app/artifacts/models.py`
- `tests/processing/test_spark_adapter.py`
- `tests/processing/test_processing_worker.py`
- `schemas/artifacts/output_manifest.schema.json`
- `schemas/examples/artifacts/output_manifest.valid.json`
- `schemas/examples/artifacts/output_manifest.invalid_enum.json`
- `docs/schemas/artifact_schemas.md`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260502-wp08-processing-worker.md`
- `docs/verification/evidence/sphinx_build.txt`

## Contract usage

- Event contracts: `schemas/events/processing_started.schema.json`, `schemas/events/processing_completed.schema.json`, `schemas/events/processing_failed.schema.json`
- Artifact contracts: `schemas/artifacts/processing_summary.schema.json`, `schemas/artifacts/output_manifest.schema.json`
- Artifact models: `app.artifacts.models.ProcessingSummary`, `app.artifacts.models.OutputManifest`
- Repositories: `ProcessingRepository`, `StageClaimRepository`, `JobRepository`, `DeliveryRepository`, `EventOutboxRepository`
- Event enqueue surface: `app.events.outbox.enqueue_event`
- No new API routes, no new environment variables, and no Docker/orchestration changes

## Tests run

Contract and schema verification:

```powershell
python -S tools/contract_lint.py --write-inventory
```

Result: passed.

```powershell
& '.\.venv\Scripts\python.exe' tools/validate_schema_examples.py --write-evidence
```

Result: passed, `169` examples validated and `169` passed.

```powershell
$env:PATH = "${PWD}\.venv\Scripts;" + $env:PATH; & '.\.venv\Scripts\python.exe' tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
```

Result: passed, Sphinx exit code `0`.

Pytest:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest tests/processing -q
```

Result: `11 passed, 1 warning in 0.39s`.

The default Windows pytest temp root is permission-broken in this environment, so the remaining required pytest runs used an inline repo-local `tmp_path` override while keeping the test targets unchanged:

```powershell
tests/validation -q
tests/watcher -q
tests/events -q
tests/repositories -q
tests/config tests/api tests/observability -q
tests/schemas -q
tests/db -q
tests/contract -q
tests -q
```

Results:

- `tests/validation -q`: `16 passed, 1 warning in 0.40s`
- `tests/watcher -q`: `11 passed, 1 warning in 0.35s`
- `tests/events -q`: `8 passed, 1 warning in 0.30s`
- `tests/repositories -q`: `6 passed, 1 warning in 0.28s`
- `tests/config tests/api tests/observability -q`: `55 passed, 1 warning in 2.04s`
- `tests/schemas -q`: `213 passed, 1 warning in 0.36s`
- `tests/db -q`: `3 passed, 1 warning in 0.26s`
- `tests/contract -q`: `3 passed, 1 warning in 0.13s`
- `tests -q`: `326 passed, 1 warning in 3.09s`

## Assumptions

- The WP-08 adapter is a deterministic local Spark-profile demo and does not require live Spark execution.
- Flink remains deferred and no Flink adapter is activated.
- No new processing-root setting or env var is added; the adapter uses constructor-configurable `processing_root` with default `/stream-lite/processing`.
- `claim_and_process` is the callable MVP surface; no scheduler loop, background daemon, or service runner is introduced.
- Delivery remains out of scope for WP-08, so the output manifest is persisted with `destination_outcomes=[]` and `status=processed`.

## Gaps

- The Windows sandbox temp-root issue required a repo-local pytest `tmp_path` override for the non-processing suites; the application code is unaffected, but the exact bare `pytest ...` invocations are not stable in this environment without that override.
- Processing worker concurrency configuration and graceful shutdown behavior from later processing requirements remain deferred because this patch implements only the callable WP-08 worker surface requested by the prompt.

## Rollback notes

- Revert `app/processing/`, the output-manifest contract updates, the processing tests, the schema/doc updates, and this worklog/index entry to remove WP-08.
- If demo-state cleanup is required after rollback, remove processing attempts, processing-stage claims, output-manifest rows, and generated processing artifacts through an approved non-destructive migration or fixture reset workflow rather than ad hoc recursive deletion.

## Next step

WP-08 is ready to hand off to WP-09 delivery work. WP-09 should consume the persisted pre-delivery output manifest, populate destination outcomes, and own the transition from `PROCESSED` into delivery-terminal states.
