# REQ-006: Job Metadata and State Requirements

## Capability Intent

The system shall maintain a durable operational source of truth for watcher configuration, file identities, job state, processing attempts, validation outcomes, delivery outcomes, retry schedules, and audit logs.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-JOB-001 | PostgreSQL shall be the source of truth for current job state. | Must | V-SL-JOB-001 |
| SL-JOB-002 | Each job shall have a globally unique `job_id` generated as UUIDv7 or UUIDv4 at registration time. | Must | V-SL-JOB-002 |
| SL-JOB-003 | Each job shall reference exactly one watcher ID and exactly one source folder ID. | Must | V-SL-JOB-003 |
| SL-JOB-004 | Each job shall store source file identity fields: source folder ID, sanitized display path, container locator, file name, extension, byte size, content hash, detected timestamp, and stable timestamp. | Must | V-SL-JOB-004 |
| SL-JOB-005 | Each job shall store current state and terminal state when applicable. | Must | V-SL-JOB-005 |
| SL-JOB-006 | Each state transition shall append an immutable state history record. | Must | V-SL-JOB-006 |
| SL-JOB-007 | Invalid state transitions shall be rejected. | Must | V-SL-JOB-007 |
| SL-JOB-008 | Processing attempts shall be recorded with attempt number, engine, start time, end time, status, error code, and output locator when status is `processed` and `null` when status is `failed` before output creation. | Must | V-SL-JOB-008 |
| SL-JOB-009 | Delivery attempts shall be recorded with destination ID, attempt number, start time, end time, status, and delivered locator when status is `delivered` and `null` before delivery finalization. | Must | V-SL-JOB-009 |
| SL-JOB-010 | Retry schedules shall be persisted before a job enters `RETRY_PENDING`. | Must | V-SL-JOB-010 |
| SL-JOB-011 | The system shall expose list and filter operations by state, watcher ID, file name, created time range, and terminal status. | Must | V-SL-JOB-011 |
| SL-JOB-012 | Job records shall be queryable after API, watcher, processor, or dashboard restart. | Must | V-SL-JOB-012 |
| SL-JOB-013 | The system shall persist event outbox records, command records, duplicate-suppression observations, and stage ownership claims so service handoffs remain reconstructable after restart. | Must | V-SL-JOB-013 |
| SL-JOB-014 | A worker shall claim a job stage by inserting or updating a stage ownership record with service name, stage, attempt number, lease expiration timestamp, and claim status before performing side effects. | Must | V-SL-JOB-014 |
| SL-JOB-015 | Expired stage ownership leases shall be recoverable by another eligible worker only after the previous lease expiration timestamp has passed and the recovery is logged. | Must | V-SL-JOB-015 |

## State Transition Rules

| From | Allowed To |
|---|---|
| `DETECTED` | `STABILIZING`, `FAILED` |
| `STABILIZING` | `REGISTERED`, `FAILED` |
| `REGISTERED` | `VALIDATING`, `FAILED` |
| `VALIDATING` | `VALIDATED`, `INVALID`, `FAILED` |
| `VALIDATED` | `PROCESSING`, `FAILED` |
| `PROCESSING` | `PROCESSED`, `RETRY_PENDING`, `FAILED` |
| `PROCESSED` | `DELIVERING`, `FAILED` |
| `DELIVERING` | `DELIVERED`, `COMPLETED_WITH_DELIVERY_ERRORS`, `RETRY_PENDING`, `FAILED` |
| `DELIVERED` | `COMPLETED` |
| `INVALID` | `QUARANTINED` |
| `RETRY_PENDING` | `VALIDATING`, `PROCESSING`, `DELIVERING`, `FAILED` |
| `COMPLETED_WITH_DELIVERY_ERRORS` | none |
| `COMPLETED` | none |
| `FAILED` | none |
| `QUARANTINED` | none |

## Job State Rules

| Rule | Requirement |
|---|---|
| Timestamp format | All persisted timestamps shall be UTC ISO-8601 with timezone offset or PostgreSQL `timestamptz`. |
| Terminal states | Terminal states for MVP are `COMPLETED`, `COMPLETED_WITH_DELIVERY_ERRORS`, `FAILED`, and `QUARANTINED`. |
| State history immutability | State history rows shall not be updated or deleted by application code; corrections shall be represented by a new state history row. |
| Invalid transition response | API or worker attempts to perform an invalid state transition shall fail with `409 INVALID_STATE_TRANSITION`, log the attempted transition, and leave current state unchanged. |
| Current state derivation | `jobs.current_state` shall match the latest committed state history row for the same `job_id`; verification shall check this invariant. |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-JOB-NFR-001 | Job insert p95 latency | <= 100 ms |
| SL-JOB-NFR-002 | Job state update p95 latency | <= 100 ms |
| SL-JOB-NFR-003 | Dashboard list query p95 latency for <= 10,000 jobs | <= 300 ms |
| SL-JOB-NFR-004 | State history completeness | 100% of state transitions |
| SL-JOB-NFR-005 | Invalid state transition rejection | 100% for transition fixture matrix |
| SL-JOB-NFR-006 | Metadata survival across container restart | 100% committed records |

## L2 Contract Decomposition Requirements

These rows decompose durable job state into identity, transition, attempt, command/outbox, ownership, and query contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-JOB-025 | L2 | SL-JOB-001, SL-JOB-002, SL-JOB-003, SL-JOB-004 | Job identity contract | Job creation shall assign a unique job ID, associate exactly one watcher and source folder, persist immutable source identity fields, and reject missing or ineligible references. | Must | V-SL-JOB-025 |
| SL-JOB-026 | L2 | SL-JOB-005, SL-JOB-006, SL-JOB-007, SL-JOB-017, SL-JOB-018 | State transition contract | State transitions shall atomically update current state, append history, enforce the transition matrix, preserve transition sequence, and reject invalid transitions with `409 INVALID_STATE_TRANSITION`. | Must | V-SL-JOB-026 |
| SL-JOB-027 | L2 | SL-JOB-008, SL-JOB-009, SL-JOB-019, SL-JOB-020 | Stage attempt contract | Validation, processing, and delivery attempt records shall use stage-local attempt numbers, record start and terminal timestamps, status, error code, and related transition or retry schedule. | Must | V-SL-JOB-027 |
| SL-JOB-028 | L2 | SL-JOB-010, SL-JOB-013, SL-JOB-021, SL-JOB-022 | Command and outbox durability contract | Control commands and event outbox rows shall be persisted before enqueue/publish side effects and expose status, attempt count, next action timestamp, and last error code for recovery. | Must | V-SL-JOB-028 |
| SL-JOB-029 | L2 | SL-JOB-014, SL-JOB-015 | Stage ownership lease contract | Stage ownership claims shall include owner service, stage, attempt, lease expiration, claim status, and recovery metadata before any worker side effect. | Must | V-SL-JOB-029 |
| SL-JOB-030 | L2 | SL-JOB-011, SL-JOB-012, SL-JOB-024 | Job query contract | Job list/detail queries shall read durable tables, support documented filters, return deterministic ordering, include latest state/error summary, and remain available after restart. | Must | V-SL-JOB-030 |

## L3 Persistence and Repository Decomposition Requirements

These rows decompose the migration table contracts into repository-facing implementation surfaces. They do not create runtime code; they define what future repository functions must own and verify.

| ID | Level | Parent requirement IDs | Table / repository surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-JOB-031 | L3 | SL-JOB-016, SL-FWM-020 | `watchers` repository | The watcher repository surface shall create and update watcher identity, lifecycle state, operational status, route policy, enabled flag, and audit timestamps using application-generated `watcher_id`. | Must | V-SL-JOB-031 |
| SL-JOB-032 | L3 | SL-JOB-016, SL-FWM-020 | `watcher_sources` repository | The watcher source repository surface shall persist source folder IDs, normalized paths, display paths, original route tag text, normalized route tags, health status, and reason code without host-only paths. | Must | V-SL-JOB-032 |
| SL-JOB-033 | L3 | SL-JOB-016, SL-FWM-021 | `watcher_destinations` repository | The watcher destination repository surface shall persist destination folder IDs, normalized paths, display paths, original route tag text, normalized route tags, health status, and reason code without host-only paths. | Must | V-SL-JOB-033 |
| SL-JOB-034 | L3 | SL-JOB-016, SL-FWM-026 | `watcher_route_matches` repository | The route match repository surface shall persist previewed and enabled source-to-destination matches, unmatched reasons, route policy, and route tag evidence for deterministic dashboard/API route previews. | Must | V-SL-JOB-034 |
| SL-JOB-035 | L3 | SL-JOB-004, SL-FDI-015 | `files` repository | The file repository surface shall persist immutable file identity, byte size, content hash, first-seen timestamp, stable timestamp, source folder reference, and deduplication key before job creation. | Must | V-SL-JOB-035 |
| SL-JOB-036 | L3 | SL-JOB-001, SL-JOB-002, SL-JOB-003, SL-JOB-005 | `jobs` repository | The job repository surface shall create application-generated `job_id` records, persist current state and latest summary fields, enforce required watcher/file/source references, and support state-filtered queries. | Must | V-SL-JOB-036 |
| SL-JOB-037 | L3 | SL-JOB-006, SL-JOB-007, SL-LIFE-009 | `job_state_history` repository | The state history repository surface shall append immutable transition rows with transition sequence, prior/new state, actor service, reason code, event ID, timestamp, and correlation ID in the same transaction as current-state updates. | Must | V-SL-JOB-037 |
| SL-JOB-038 | L3 | SL-JOB-019, SL-VAL-010 | `validation_attempts` repository | The validation attempt repository surface shall persist stage-local attempt number, validation status, rule results, reason codes, duration seconds, timestamps, and correlation ID. | Must | V-SL-JOB-038 |
| SL-JOB-039 | L3 | SL-JOB-019, SL-VAL-016 | `quarantine_records` repository | The quarantine repository surface shall persist quarantine record ID, source display path, quarantine locator, reason codes, copy status, timestamps, and operator message before `file.quarantined` is published. | Must | V-SL-JOB-039 |
| SL-JOB-040 | L3 | SL-JOB-008, SL-PRO-016 | `processing_attempts` repository | The processing attempt repository surface shall persist engine, engine version, attempt number, input/output locators, status, row counts when available, duration seconds, and error code. | Must | V-SL-JOB-040 |
| SL-JOB-041 | L3 | SL-DCT-011, SL-OUT-010 | `output_manifests` repository | The output manifest repository surface shall persist manifest locator, produced output locators, source checksum, output checksum, destination outcome summary, finalized timestamp, and status. | Must | V-SL-JOB-041 |
| SL-JOB-042 | L3 | SL-JOB-020, SL-OUT-006, SL-OUT-018 | `delivery_attempts` repository | The delivery attempt repository surface shall persist one row per destination attempt with destination folder ID, matched route tags, temporary/final locators, checksum, status, failure code, and attempt timestamps. | Must | V-SL-JOB-042 |
| SL-JOB-043 | L3 | SL-JOB-010, SL-RET-006 | `retry_schedules` repository | The retry schedule repository surface shall persist failed stage, failure class, due time, backoff seconds, attempt number, max attempts, jitter flag, status, and next-stage eligibility. | Must | V-SL-JOB-043 |
| SL-JOB-044 | L3 | SL-JOB-022, SL-LIFE-001, SL-LIFE-015 | `control_commands` repository | The command repository surface shall persist accepted command records, target resource type/ID, requested-by, operator reason, idempotency key, status, timestamps, result locator, and error code for dashboard polling. | Must | V-SL-JOB-044 |
| SL-JOB-045 | L3 | SL-API-007, SL-LIFE-024 | `idempotency_keys` repository | The idempotency repository surface shall persist scoped idempotency keys, payload hash, target resource, first response metadata, expiration policy, and duplicate-detection timestamps. | Must | V-SL-JOB-045 |
| SL-JOB-046 | L3 | SL-JOB-014, SL-JOB-015, SL-LIFE-017 | `stage_ownership_claims` repository | The stage ownership repository surface shall persist claim ID, job ID, stage, attempt number, owner service, lease expiration, claim status, and recovery metadata before worker side effects. | Must | V-SL-JOB-046 |
| SL-JOB-047 | L3 | SL-JOB-023, SL-LIFE-013 | `duplicate_suppression_observations` repository | The duplicate observation repository surface shall persist duplicate arrival evidence linked to an existing job without creating a new lifecycle or emitting job lifecycle events. | Must | V-SL-JOB-047 |
| SL-JOB-048 | L3 | SL-JOB-021, SL-EVT-011 | `event_outbox` repository | The event outbox repository surface shall persist application-generated `outbox_id` and `event_id`, stream name, event type, full envelope, payload JSON, publish status, next publish time, attempt count, and last error code. | Must | V-SL-JOB-048 |
| SL-JOB-049 | L3 | SL-EVT-006, SL-EVT-015 | `event_offsets` repository | The event offset repository surface shall persist consumer group, stream name, Redis stream ID, last processed event ID, updated timestamp, and uniqueness by consumer group plus stream name. | Must | V-SL-JOB-049 |
| SL-JOB-050 | L3 | SL-JOB-024, SL-OBS-008 | `operational_log_summaries` repository | The operational log summary repository surface shall persist bounded-cardinality log summaries, optional job/watcher references, event name, error code, sanitized message, and timestamp for `GET /logs`. | Must | V-SL-JOB-050 |
| SL-JOB-051 | L3 | SL-RUN-013, SL-FWM-018, SL-OBS-013 | `health_observations` repository | The health observation repository surface shall persist dependency and folder health observations, status, reason code, checked timestamp, and optional watcher/folder reference for dashboard health summaries. | Must | V-SL-JOB-051 |

## Acceptance Criteria

The requirement is accepted when state transition tests prove valid paths succeed, invalid paths fail, every state change writes history, and the dashboard/API can recover the same job state after container restart.

## 2026-04-25 Logical Data Model Decomposition Requirements

These rows decompose `docs/data/logical_model.md` into owning job/data requirements so database implementation tasks do not infer table ownership or handoff semantics.

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-JOB-016 | The `watchers`, `watcher_sources`, and `watcher_destinations` tables shall persist route policy, original route tag text, normalized route tags, lifecycle state, operational status, latest health check status, and latest route preview timestamp. | Must | V-SL-JOB-016 |
| SL-JOB-017 | The `jobs` table shall persist only current state and current summary fields; full transition history shall be persisted in `job_state_history`. | Must | V-SL-JOB-017 |
| SL-JOB-018 | The `job_state_history` table shall include `history_id`, `job_id`, `previous_state`, `new_state`, `actor_service`, `reason_code`, `transition_sequence`, `transitioned_at`, and `correlation_id`. | Must | V-SL-JOB-018 |
| SL-JOB-019 | The `validation_attempts`, `processing_attempts`, and `delivery_attempts` tables shall use stage-local monotonically increasing `attempt_number` values scoped to `job_id` and stage. | Must | V-SL-JOB-019 |
| SL-JOB-020 | The `delivery_attempts` table shall persist one row per destination attempt with `destination_folder_id`, `matched_route_tags`, `status`, `temporary_locator`, `finalized_locator`, `manifest_locator`, `checksum_sha256`, and `failure_code`. | Must | V-SL-JOB-020 |
| SL-JOB-021 | The `event_outbox` table shall persist `outbox_id`, `event_id`, `event_type`, `stream_name`, `job_id`, `watcher_id`, `payload_json`, `status`, `publish_attempts`, `next_publish_at`, `published_stream_id`, and `last_error_code`. | Must | V-SL-JOB-021 |
| SL-JOB-022 | The `control_commands` table shall persist `command_id`, `command_type`, `target_resource_type`, `target_resource_id`, `requested_by`, `operator_reason`, `idempotency_key`, `status`, `created_at`, `updated_at`, `completed_at`, `result_locator`, and `error_code`. | Must | V-SL-JOB-022 |
| SL-JOB-023 | The `duplicate_suppression_observations` table shall record duplicate arrivals without creating new jobs and shall include `existing_job_id`, `watcher_id`, `source_folder_id`, `source_display_path`, `byte_size`, `content_hash`, `observed_at`, and reason code `DUPLICATE_SUPPRESSED`. | Must | V-SL-JOB-023 |
| SL-JOB-024 | The `operational_log_summaries` table shall persist dashboard-queryable summaries of structured logs with bounded-cardinality fields only; raw full log retention is outside v0.1 unless added by a later requirement. | Must | V-SL-JOB-024 |

## Required Table-to-Service Write Ownership

| Table | Service allowed to insert/update business fields | Services allowed read access |
|---|---|---|
| `watchers` | FastAPI | all services through repository/query layer |
| `watcher_sources` | FastAPI; watcher may update health fields only | all services through repository/query layer |
| `watcher_destinations` | FastAPI; delivery may update health fields only | all services through repository/query layer |
| `jobs` | watcher for creation; stage owners for owned state transitions | all services through repository/query layer |
| `job_state_history` | stage owner performing transition | all services through repository/query layer |
| `validation_attempts` | validation service | API, dashboard, retry scheduler |
| `processing_attempts` | processing worker | API, dashboard, delivery, retry scheduler |
| `delivery_attempts` | delivery service | API, dashboard, retry scheduler |
| `retry_schedules` | retry scheduler | API, dashboard, workers |
| `event_outbox` | stage owner creates; event dispatcher updates publication fields only | API, dashboard, event dispatcher |
| `event_offsets` | event consumers | API, dashboard |
| `control_commands` | FastAPI creates; command processor/retry scheduler updates status fields | API, dashboard |
| `stage_ownership_claims` | worker that owns the stage | API, dashboard, retry scheduler |
| `duplicate_suppression_observations` | watcher | API, dashboard |
| `quarantine_records` | validation service | API, dashboard |
| `operational_log_summaries` | all services via logging adapter | API, dashboard |
