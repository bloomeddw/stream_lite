# WP-08 Reference Map: Processing Worker

## Purpose

Reduce Codex reasoning for WP-08 by fixing the processing stage boundaries, Spark-profile adapter responsibilities, artifact writing, event outputs, and tests.

## Scope boundary

WP-08 implements processing of validated jobs through a callable worker primitive. It claims processing work, records attempts, writes processing summary artifacts, updates job state, and enqueues processing events.

WP-08 must not implement watcher, validation, delivery, retry scheduler, API routes, Streamlit pages, or Docker orchestration changes unless already documented.

## Primary requirement IDs

- `SL-PRO-001` through `SL-PRO-029`
- `SL-JOB-040`
- `SL-LIFE-008`
- `SL-OBS-005`
- `SL-EVT-006`, `SL-EVT-007`, `SL-EVT-008`
- `SL-DCT-001` through `SL-DCT-033` where schema validation is reused

## Read before coding

- `docs/reqs/REQ-007-processing-engine-spark-flink.md`
- `docs/design/DEC-004-mvp-processing-engine.md`
- `docs/operations/fault_tolerance.md`
- `app/repositories/processing.py`
- `app/repositories/stage_claims.py`
- `app/repositories/jobs.py`
- `app/events/outbox.py`
- `schemas/events/processing_started.schema.json`
- `schemas/events/processing_completed.schema.json`
- `schemas/events/processing_failed.schema.json`
- `schemas/artifacts/processing_summary.schema.json`

## Target modules

| Module | Responsibility |
|---|---|
| `app/processing/__init__.py` | Export WP-08 processing surfaces. |
| `app/processing/engine.py` | Business-neutral processing worker orchestration. |
| `app/processing/spark_adapter.py` | Spark-profile POC processing adapter. |
| `tests/processing/test_spark_adapter.py` | Adapter behavior with local temp inputs/outputs. |
| `tests/processing/test_processing_worker.py` | Claim, attempt, event, state, and artifact tests. |

## Fixed implementation map

### Processing worker callable

Implement `ProcessingWorker.process_one(job_id, correlation_id=None)` or `claim_and_process(limit=1)` depending on repository support.

Flow:

1. Acquire processing stage claim for job.
2. Load job/source metadata.
3. Create processing attempt row.
4. Enqueue `processing.started`.
5. Invoke processing adapter.
6. On success: write `processing_summary.json`, persist processing attempt success, update job state to `PROCESSED`, append history, enqueue `processing.completed`.
7. On failure: persist failure attempt, update job state according to failure policy, enqueue `processing.failed`.
8. Release stage claim.

Do not schedule retry directly; retry scheduler handles retries in WP-10.

### Spark adapter

For MVP, adapter may be a deterministic local/demo transformation as long as it is documented as Spark-profile POC behavior and satisfies `REQ-007`. Do not require a live Spark cluster in unit tests unless the repo already provides one.

Adapter output:

- output locator
- row/record counts when available
- byte count when available
- duration seconds
- engine/version metadata

### Artifact writer

Write `processing_summary.json` with fields from `schemas/artifacts/processing_summary.schema.json` and validate before persisting final attempt state.

## Events/artifacts produced

| Output | Producer | Notes |
|---|---|---|
| `processing.started` | `processor` | Before adapter execution. |
| `processing.completed` | `processor` | After successful summary artifact write. |
| `processing.failed` | `processor` | After adapter or artifact failure. |
| `processing_summary.json` | `ProcessingSummaryWriter` | Must validate against artifact schema. |

## Repository use

| Repository | Required WP-08 use |
|---|---|
| `ProcessingRepository` | Create/update processing attempts and summary references. |
| `StageClaimRepository` | Claim/release processing stage. |
| `JobRepository` | Load/update job and append state history. |
| `EventOutboxRepository` | Indirectly via `app/events/outbox.py`. |

## Test checklist

- Successful processing writes output artifact and processing summary.
- Processing summary validates against JSON schema and Pydantic artifact model.
- `processing.started` and `processing.completed` events are enqueued on success.
- Adapter failure enqueues `processing.failed` and stores failure attempt.
- Stage claim is released on success and failure.
- Worker does not start delivery directly.
- Unsafe locators/paths are rejected.

## Out of scope

- Delivery fanout.
- Retry scheduling execution.
- API or Streamlit changes.
- Live Spark cluster orchestration unless already provided.

## Verification commands

Run the standard suite plus:

```powershell
pytest tests/processing
```
