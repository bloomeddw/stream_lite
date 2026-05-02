# REQ-017: End-to-End Lifecycle and Handoff Orchestration Requirements

## Capability Intent

Stream Lite shall define the complete job lifecycle as an explicit sequence of durable handoffs between bounded services. Each handoff shall identify the owning service, trigger event or command, required input state, database side effect, emitted event, retry behavior, idempotency rule, and reconciliation behavior so implementation agents do not invent incompatible stage transitions.

## Scope

In scope for v0.1:
- Happy path from watcher start through completed delivery.
- Invalid-file quarantine path.
- Duplicate-arrival suppression path.
- Retryable processing and delivery failure paths.
- Outbox-backed event publication.
- Command acceptance versus command completion.
- Reconciliation loops for missed events or service restarts.

Out of scope for v0.1:
- User-driven cancellation of already registered jobs.
- Editing a quarantined file and reprocessing it as a new job.
- Cross-host distributed leadership election.

## Lifecycle Handoff Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-LIFE-001 | A watcher lifecycle command shall be persisted as a command record before the watcher service changes watcher lifecycle state. | Must | V-SL-LIFE-001 |
| SL-LIFE-002 | An active watcher shall create a `DETECTED` job record before emitting `file.detected`. | Must | V-SL-LIFE-002 |
| SL-LIFE-003 | The watcher shall move a detected file through `STABILIZING` and `REGISTERED`; validation shall not start before `REGISTERED` is committed. | Must | V-SL-LIFE-003 |
| SL-LIFE-004 | Validation shall consume `job.registered` or reconcile unvalidated `REGISTERED` jobs, then move jobs through `VALIDATING` to `VALIDATED` or `INVALID`. | Must | V-SL-LIFE-004 |
| SL-LIFE-005 | Quarantine shall occur only after `INVALID` is committed and shall finish by transitioning the job to `QUARANTINED` after the quarantine record and copy status are durable. | Must | V-SL-LIFE-005 |
| SL-LIFE-006 | Processing shall consume `file.validated` or reconcile eligible `VALIDATED` jobs, then move jobs through `PROCESSING` to `PROCESSED`, `RETRY_PENDING`, or `FAILED`. | Must | V-SL-LIFE-006 |
| SL-LIFE-007 | Delivery shall consume `processing.completed` or reconcile eligible `PROCESSED` jobs, then move jobs through `DELIVERING` to `DELIVERED`, `COMPLETED_WITH_DELIVERY_ERRORS`, `RETRY_PENDING`, or `FAILED`. | Must | V-SL-LIFE-007 |
| SL-LIFE-008 | Completion shall transition `DELIVERED` jobs to `COMPLETED` only after all required destination delivery attempts have terminal successful outcomes. | Must | V-SL-LIFE-008 |
| SL-LIFE-009 | A job shall never skip a required state in the state model; each lifecycle stage shall append a state history row and an outbox event in the same transaction. | Must | V-SL-LIFE-009 |
| SL-LIFE-010 | A retry scheduler shall move due `RETRY_PENDING` jobs back to the next eligible stage based on latest failed stage and retry schedule, without changing `job_id`. | Must | V-SL-LIFE-010 |
| SL-LIFE-011 | Each service shall run a reconciliation query for its eligible input states at least every 10 seconds and after service startup. | Must | V-SL-LIFE-011 |
| SL-LIFE-012 | Reconciliation shall be idempotent and shall not create duplicate attempts, duplicate finalized outputs, or duplicate terminal state history rows. | Must | V-SL-LIFE-012 |
| SL-LIFE-013 | A duplicate file arrival shall not create a new lifecycle; it shall create a duplicate-suppression observation linked to the existing job and shall not emit job lifecycle events. | Must | V-SL-LIFE-013 |
| SL-LIFE-014 | Every handoff shall carry `correlation_id`, `job_id`, `watcher_id`, `source_folder_id` when job-scoped, and `attempt_number` when stage-scoped. | Must | V-SL-LIFE-014 |
| SL-LIFE-015 | A command shall reach terminal command status `succeeded`, `failed`, or `expired` within 30 seconds for watcher lifecycle commands and within 10 seconds for retry-command acceptance. | Must | V-SL-LIFE-015 |
| SL-LIFE-016 | If a command fails after acceptance, the command status shall include `error_code`, operator-safe message, target resource ID, and correlation ID; the API shall not hide the failure behind the original `202` response. | Must | V-SL-LIFE-016 |

## Required Handoff Matrix

| Stage | Owning service | Trigger | Required input state | Durable side effect | Emitted event |
|---|---|---|---|---|---|
| Watcher start | API + watcher | `watcher.start` command | watcher `created`, `stopped`, or `error` and valid route preview | command record; watcher lifecycle `active` or command failure | `watcher.lifecycle_changed` if event schema is active; otherwise command status only |
| File detection | watcher | filesystem observation | watcher `active`; source health not red; matched destination exists | job row in `DETECTED`; state history; outbox | `file.detected` |
| Stability | watcher | stability timer | `DETECTED` | state `STABILIZING`, then `REGISTERED`; stable metadata | `file.stable`, `job.registered` |
| Validation | validator | `job.registered` or reconciliation | `REGISTERED` | validation attempt; state `VALIDATING`, then `VALIDATED` or `INVALID` | `file.validated` or `job.state_changed` |
| Quarantine | validator | invalid validation result | `INVALID` | quarantine copy result; quarantine record; state `QUARANTINED` | `file.quarantined` |
| Processing | processor | `file.validated` or reconciliation | `VALIDATED` | processing attempt; staging output; processing summary; state `PROCESSED`, `RETRY_PENDING`, or `FAILED` | `processing.started`, `processing.completed`, or `processing.failed` |
| Delivery | delivery | `processing.completed` or reconciliation | `PROCESSED` | delivery attempts; manifests; state `DELIVERED`, `COMPLETED_WITH_DELIVERY_ERRORS`, `RETRY_PENDING`, or `FAILED` | `delivery.started`, `delivery.completed`, or `delivery.failed` |
| Completion | delivery | all required deliveries succeeded | `DELIVERED` | state `COMPLETED`; final manifest status | `job.completed` |
| Retry due | retry scheduler | due retry schedule | `RETRY_PENDING` | new stage attempt; state to `VALIDATING`, `PROCESSING`, or `DELIVERING` | `retry.scheduled` plus stage event |

## Backpressure and Capacity Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-LIFE-017 | Each worker service shall have a documented local concurrency limit; default v0.1 values shall be watcher scans `1` per watcher, validation workers `2`, processing workers `1`, delivery workers `2`, and outbox dispatcher workers `1`. | Must | V-SL-LIFE-017 |
| SL-LIFE-018 | When an input stage has more eligible jobs than its concurrency limit, excess jobs shall remain in their current durable state and shall not be dropped from the queue. | Must | V-SL-LIFE-018 |
| SL-LIFE-019 | The system shall expose queue lag or eligible-job count metrics for validation, processing, delivery, retry, and outbox publication stages. | Must | V-SL-LIFE-019 |
| SL-LIFE-020 | Backpressure shall not cause watcher source files to be deleted, moved, or modified. | Must | V-SL-LIFE-020 |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-LIFE-NFR-001 | Service reconciliation interval | <= 10 seconds |
| SL-LIFE-NFR-002 | Missing handoff recovery after single service restart | 100% of validation, processing, delivery, retry, and outbox stages |
| SL-LIFE-NFR-003 | Duplicate side effects under duplicate event replay | 0 duplicate attempts beyond idempotent retry records and 0 duplicate finalized outputs |
| SL-LIFE-NFR-004 | Accepted command reaches terminal command status | <= 30 seconds for lifecycle commands |
| SL-LIFE-NFR-005 | Queue lag metric availability for active stages | 100% |

## L2 Contract Decomposition Requirements

These rows decompose end-to-end orchestration into lifecycle stage, durable handoff, backpressure, idempotency, and restart-recovery contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-LIFE-021 | L2 | SL-LIFE-001, SL-LIFE-002, SL-LIFE-003 | Lifecycle stage contract | Each lifecycle stage shall define owner service, entry state, exit state, persisted records, emitted event, structured log, metric, retry behavior, and terminal failure behavior. | Must | V-SL-LIFE-021 |
| SL-LIFE-022 | L2 | SL-LIFE-004, SL-LIFE-005, SL-LIFE-006 | Durable handoff contract | Downstream work shall become visible only after upstream state, attempt records, and outbox records are committed, preventing events from referencing uncommitted records. | Must | V-SL-LIFE-022 |
| SL-LIFE-023 | L2 | SL-LIFE-007, SL-LIFE-008, SL-LIFE-009 | Backpressure contract | Backpressure shall use bounded eligible-job queries, queue lag or pending counts, watcher status, and retry scheduling rather than unbounded in-memory queues. | Must | V-SL-LIFE-023 |
| SL-LIFE-024 | L2 | SL-LIFE-010, SL-LIFE-011, SL-LIFE-012 | Idempotency contract | Replayed scans, commands, events, and worker attempts shall use persisted idempotency keys, duplicate observations, stage ownership, or command IDs to avoid duplicate side effects. | Must | V-SL-LIFE-024 |
| SL-LIFE-025 | L2 | SL-LIFE-013, SL-LIFE-014, SL-LIFE-015, SL-LIFE-020 | Restart recovery contract | After restart, services shall reconstruct pending work from PostgreSQL and Redis Streams state, resume only eligible stages, reconcile stale claims, and log recovery actions. | Must | V-SL-LIFE-025 |

## Acceptance Criteria

The requirement is accepted when an end-to-end fixture proves each stage handoff writes the documented durable state, emits events through the outbox path, survives restart at every stage boundary, suppresses duplicate arrivals without creating new jobs, exposes command status after `202 Accepted`, and reports queue lag when concurrency limits are reached.
