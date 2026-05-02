# WP-10 Reference Map: Retry Scheduler and Manual Retry

## Purpose

Reduce Codex reasoning for WP-10 by fixing retry classification, backoff, retry schedule persistence, exhausted retry handling, manual retry command behavior, and tests.

## Scope boundary

WP-10 implements retry policy primitives and manual retry acceptance/execution handoff. It does not implement API route handlers unless WP-05 already created route shells and the package explicitly wires existing services behind them.

## Primary requirement IDs

- `SL-RET-001` through `SL-RET-020`
- `SL-JOB-043`
- `SL-JOB-044`
- `SL-LIFE-014`
- `SL-EVT-017`, `SL-EVT-022`, `SL-EVT-023`
- `SL-API-037` if existing manual retry route shell is wired
- `SL-DCT-001` through `SL-DCT-033` where schemas are reused

## Read before coding

- `docs/reqs/REQ-009-retry-and-recovery.md`
- `docs/operations/retry_policy.md`
- `docs/operations/fault_tolerance.md`
- `docs/design/DEC-006-manual-retry-eligibility.md`
- `app/repositories/retry.py`
- `app/repositories/commands.py`
- `app/repositories/jobs.py`
- `app/events/outbox.py`
- `schemas/events/retry_scheduled.schema.json`
- `schemas/events/job_failed.schema.json`
- `schemas/api/retry_command_request.schema.json`
- `schemas/api/command_accepted_response.schema.json`
- `schemas/api/command_status_response.schema.json`

## Target modules

| Module | Responsibility |
|---|---|
| `app/retry/__init__.py` | Export retry surfaces. |
| `app/retry/classifier.py` | Map failure codes/classes to retryable/non-retryable. |
| `app/retry/backoff.py` | Exponential backoff with jitter bounds from existing policy. |
| `app/retry/scheduler.py` | Due retry scan, schedule creation, exhaustion handling. |
| `tests/retry/test_classifier.py` | Classification matrix. |
| `tests/retry/test_backoff.py` | Backoff/jitter/max tests. |
| `tests/retry/test_scheduler.py` | Schedule, due retry, exhaustion, and event tests. |
| `tests/retry/test_manual_retry.py` | Manual retry command eligibility/idempotency tests. |

## Fixed implementation map

### Default retry policy

Use the already documented default:

- max attempts: 3
- initial backoff: 1 second
- multiplier: 2
- max backoff: 30 seconds
- jitter for async/event retry scheduling
- validation failures quarantine immediately unless specifically marked recoverable
- exhausted retries fail final state and emit job failure/dead-letter event behavior as documented

Do not add new env vars in WP-10.

### Retry scheduler flow

For a recoverable failure:

1. Classify failure as retryable.
2. Compute next due time.
3. Persist retry schedule row.
4. Update job state to `RETRY_PENDING` if documented.
5. Enqueue `retry.scheduled`.

For due retries:

1. Load due schedule.
2. Check max attempts.
3. If attempts remain, mark schedule claimed/attempted and reset job to the target stage state.
4. If attempts exhausted, mark final failure and enqueue `job.failed`.

Do not run watcher/validator/processor/delivery business logic directly from scheduler. Scheduler only transitions state and makes work available.

### Manual retry flow

Manual retry service should:

1. Validate job is eligible by state/failure class.
2. Create command record using `CommandRepository`.
3. Apply idempotency key if supplied by existing API route/service layer.
4. Create retry schedule or transition job as documented.
5. Return command accepted/status primitives.

## Events produced

| Event | Producer | Notes |
|---|---|---|
| `retry.scheduled` | `retry_scheduler` | Recoverable failure or accepted manual retry. |
| `job.failed` | `retry_scheduler` | Exhausted or non-retryable final failure. |

## Repository use

| Repository | Required WP-10 use |
|---|---|
| `RetryRepository` | Create/list/update retry schedules. |
| `CommandRepository` | Manual retry command acceptance/status. |
| `JobRepository` | Job state update and history append. |
| `EventOutboxRepository` | Indirectly via `app/events/outbox.py`. |

## Test checklist

- Retryable failure class returns retryable.
- Non-retryable validation/quarantine class does not retry unless explicitly allowed.
- Backoff sequence respects 1s, 2s, 4s pattern and 30s cap.
- Jitter remains within documented bounds.
- Schedule creation enqueues `retry.scheduled`.
- Due retry changes state without running downstream worker code.
- Third/exhausted attempt enqueues `job.failed`.
- Manual retry rejects ineligible states.
- Manual retry command is idempotent where command idempotency is documented.

## Out of scope

- Worker execution logic.
- New API routes.
- Streamlit controls.
- Redis consumer loops.

## Verification commands

Run the standard suite plus:

```powershell
pytest tests/retry
```
