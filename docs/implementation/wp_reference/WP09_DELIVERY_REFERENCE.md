# WP-09 Reference Map: Delivery Worker

## Purpose

Reduce Codex reasoning for WP-09 by fixing delivery fanout, destination outcome, output manifest, event, repository, and test boundaries.

## Scope boundary

WP-09 copies processed outputs to matched destination folders, persists delivery attempts, writes output manifests, updates job state, and enqueues delivery/job completion events.

WP-09 must not implement processing, retry scheduler, API routes, Streamlit pages, or watcher behavior.

## Primary requirement IDs

- `SL-OUT-001` through `SL-OUT-029`
- `SL-JOB-041`
- `SL-JOB-042`
- `SL-LIFE-012`
- `SL-OBS-007`
- `SL-EVT-009`, `SL-EVT-010`, `SL-EVT-011`, `SL-EVT-012`
- `SL-DCT-001` through `SL-DCT-033` where schema validation is reused

## Read before coding

- `docs/reqs/REQ-008-output-delivery.md`
- `docs/design/DEC-001-tag-based-folder-routing.md`
- `docs/operations/fault_tolerance.md`
- `app/repositories/delivery.py`
- `app/repositories/jobs.py`
- `app/repositories/stage_claims.py`
- `app/events/outbox.py`
- `schemas/events/delivery_started.schema.json`
- `schemas/events/delivery_completed.schema.json`
- `schemas/events/delivery_failed.schema.json`
- `schemas/events/job_completed.schema.json`
- `schemas/artifacts/output_manifest.schema.json`

## Target modules

| Module | Responsibility |
|---|---|
| `app/delivery/__init__.py` | Export WP-09 delivery surfaces. |
| `app/delivery/service.py` | Delivery worker orchestration and fanout. |
| `tests/delivery/test_delivery_service.py` | Success, partial failure, and safe-path tests. |
| `tests/delivery/test_output_manifest.py` | Output manifest schema/model validation tests. |

## Fixed implementation map

### Delivery worker callable

Implement `DeliveryWorker.deliver_one(job_id, correlation_id=None)` or `claim_and_deliver(limit=1)`.

Flow:

1. Acquire delivery stage claim for processed job.
2. Load job, matched destinations, and processing output locator/summary.
3. For each matched destination:
   - validate destination path with `PathPolicy`
   - create delivery attempt row
   - enqueue `delivery.started`
   - copy output artifact/file
   - mark attempt success and enqueue `delivery.completed`, or mark failure and enqueue `delivery.failed`
4. Write `output_manifest.json` with per-destination outcomes.
5. Persist output manifest row/reference.
6. Update job state:
   - all destinations delivered: `COMPLETED`
   - some failed but at least one delivered: `COMPLETED_WITH_DELIVERY_ERRORS`
   - all failed: leave failure state consistent with retry policy and enqueue failure event if documented
7. Enqueue `job.completed` for completed final states.
8. Release stage claim.

### Destination outcome shape

Each destination outcome should include at minimum:

- `destination_folder_id`
- `display_path` or safe locator
- `matched_tags`
- `status`: `delivered`, `failed`, or `skipped`
- `reason_code` when not delivered
- output/finalized locator when delivered

Do not invent public API fields. Keep extra manifest object fields aligned with `output_manifest.schema.json` if it allows generic outcome objects.

## Events/artifacts produced

| Output | Producer | Notes |
|---|---|---|
| `delivery.started` | `delivery` | Per destination attempt. |
| `delivery.completed` | `delivery` | Per successful destination. |
| `delivery.failed` | `delivery` | Per failed destination. |
| `job.completed` | `delivery` | Final successful or partial-success job state. |
| `output_manifest.json` | `OutputManifestWriter` | Must validate against artifact schema. |

## Repository use

| Repository | Required WP-09 use |
|---|---|
| `DeliveryRepository` | Create/update delivery attempts and output manifests. |
| `JobRepository` | Load/update job and append state history. |
| `StageClaimRepository` | Claim/release delivery stage. |
| `EventOutboxRepository` | Indirectly via `app/events/outbox.py`. |

## Test checklist

- Single destination success copies output and writes manifest.
- Multi-destination success writes one manifest with all outcomes.
- Partial failure results in `COMPLETED_WITH_DELIVERY_ERRORS` and manifest records failed destination.
- All destination failures do not falsely mark job `COMPLETED`.
- Destination path outside allowlist is blocked.
- Delivery events validate against schemas/Pydantic models.
- Output manifest validates against schema/Pydantic model.
- Worker does not schedule retries directly.

## Out of scope

- Retry scheduling.
- API/Streamlit changes.
- Processing adapter.

## Verification commands

Run the standard suite plus:

```powershell
pytest tests/delivery
```
