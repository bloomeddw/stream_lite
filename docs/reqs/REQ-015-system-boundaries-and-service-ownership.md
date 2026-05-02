# REQ-015: System Boundaries and Service Ownership Requirements

## Capability Intent

Stream Lite shall define explicit service boundaries so implementation agents do not merge command-plane, event-plane, metadata-plane, processing-plane, and delivery-plane responsibilities into ad hoc cross-service behavior. Each service shall own a bounded set of decisions, interfaces, persistence writes, events, logs, and metrics.

## Scope

In scope for v0.1:
- Docker Compose service boundaries.
- Allowed and forbidden cross-service access.
- Ownership of state transitions and filesystem side effects.
- Dashboard/API/worker separation.
- Boundary verification through static review and integration tests.

Out of scope for v0.1:
- Kubernetes network policy.
- Multi-tenant authorization boundaries.
- Cross-host distributed deployment.

## Service Boundary Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-BND-001 | The Streamlit dashboard shall call FastAPI for all system mutations and shall not write directly to PostgreSQL, Redis Streams, Redpanda, source folders, destination folders, or quarantine folders. | Must | V-SL-BND-001 |
| SL-BND-002 | FastAPI shall own command validation, watcher configuration mutations, manual retry commands, dashboard presentation configuration responses, and read APIs for operational state. | Must | V-SL-BND-002 |
| SL-BND-003 | FastAPI shall not perform long-running file processing, Spark work, delivery copying, or watcher polling inside request handlers. | Must | V-SL-BND-003 |
| SL-BND-004 | The watcher service shall own source-folder scanning, file stability checks, source file fingerprinting, initial job registration requests or writes, and file-detected/file-stable event publication. | Must | V-SL-BND-004 |
| SL-BND-005 | The validation service shall own validation attempts, validation reason codes, quarantine record creation, quarantine file copy, and validation/quarantine events. | Must | V-SL-BND-005 |
| SL-BND-006 | The processing worker shall own Spark processing attempts, staged output creation, processing summaries, processing state transitions, and processing events. | Must | V-SL-BND-006 |
| SL-BND-007 | The delivery service shall own destination route resolution at delivery time, per-destination copy/finalization attempts, delivery manifests, and delivery events. | Must | V-SL-BND-007 |
| SL-BND-008 | PostgreSQL shall be the source of truth for watcher configuration, job current state, state history, validation attempts, processing attempts, delivery attempts, retry schedules, idempotency keys, and consumed event offsets. | Must | V-SL-BND-008 |
| SL-BND-009 | Redis Streams shall coordinate asynchronous work and shall not be treated as the source of truth for current job state. | Must | V-SL-BND-009 |
| SL-BND-010 | Source folders shall be read-only to Stream Lite services except for file open/read operations; no v0.1 service shall delete, move, rename, or rewrite source files. | Must | V-SL-BND-010 |
| SL-BND-011 | Destination folders shall be written only by the delivery service using job-scoped output paths and atomic finalize behavior defined by REQ-008. | Must | V-SL-BND-011 |
| SL-BND-012 | Quarantine folders shall be written only by the validation service using the quarantine path contract defined by REQ-004. | Must | V-SL-BND-012 |
| SL-BND-013 | Every service-to-service command or event handoff shall include `correlation_id` and shall persist enough state to resume or reject duplicate work after a container restart. | Must | V-SL-BND-013 |
| SL-BND-014 | A service shall return or log `BOUNDARY_VIOLATION` when it receives a request to perform behavior assigned to another service boundary. | Must | V-SL-BND-014 |
| SL-BND-015 | The event dispatcher shall own publishing `event_outbox` records to Redis Streams and shall not mutate job business state except outbox publication status. | Must | V-SL-BND-015 |
| SL-BND-016 | The retry scheduler shall own detection of due `RETRY_PENDING` jobs and accepted commands and shall enqueue the next eligible stage without performing validation, processing, or delivery side effects inline. | Must | V-SL-BND-016 |
| SL-BND-017 | Each service handoff shall be reconstructable from PostgreSQL records plus Redis Stream offsets after any single service restart. | Must | V-SL-BND-017 |

## Service Ownership Matrix

| Service | Owns | Shall not own |
|---|---|---|
| Streamlit dashboard | Operator display, form input, dashboard session theme/layout selection, API calls. | Database writes, broker acknowledgements, filesystem copying, processing execution. |
| FastAPI | Control-plane validation, persisted watcher mutations, read APIs, command acceptance, OpenAPI. | Long-running worker loops, source scanning, Spark execution, destination finalization. |
| Watcher | Source scanning, stability checks, file registration, idle observations. | Quarantine, processing, delivery finalization, dashboard rendering. |
| Validation | File validation, validation attempts, quarantine copy and records. | Processing transformations, destination delivery, watcher lifecycle commands. |
| Worker | Spark job execution, processing summaries, staged outputs. | Watcher configuration mutation, dashboard presentation settings, delivery finalization. |
| Delivery | Route resolution at delivery time, per-destination output delivery, delivery manifests. | Source scanning, validation rules, Spark execution. |
| PostgreSQL | Durable operational state. | External file content storage. |
| Redis Streams | Durable event coordination for v0.1. | Source of truth for current state. |
| Event dispatcher | Publish outbox events to Redis Streams and update outbox publication status. | Business state transitions unrelated to outbox publication. |
| Retry scheduler | Find due retry schedules and accepted commands, enqueue next eligible stage. | Perform validation, Spark processing, or destination delivery inline. |

## Boundary Failure Contract

| Boundary failure | Required response |
|---|---|
| Dashboard attempts direct mutation outside API | Static review/test fails `V-SL-BND-001`; no runtime credential shall be present for direct DB or broker writes. |
| API handler attempts long-running processing | API contract test fails if handler blocks past timeout or invokes processor module directly. |
| Worker receives command-plane mutation | Worker logs `BOUNDARY_VIOLATION`, rejects the message, and increments boundary violation metric. |
| Service lacks durable restart state for a handoff | Verification fails `V-SL-BND-013` until database state or idempotency record is added. |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-BND-NFR-001 | Direct dashboard database/broker/filesystem mutation paths | 0 in static review |
| SL-BND-NFR-002 | API request handlers that perform Spark execution or delivery copy | 0 in static review |
| SL-BND-NFR-003 | Boundary ownership matrix coverage for active services | 100% |
| SL-BND-NFR-004 | Restart-resumable handoff tests for event-driven stages | 100% of validation, processing, delivery stages |

## L2 Contract Decomposition Requirements

These rows decompose service boundaries into ownership, cross-service read, command handoff, event handoff, and failure/reconciliation contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-BND-018 | L2 | SL-BND-001, SL-BND-002, SL-BND-003 | Service ownership contract | Each service shall have documented ownership for commands, data tables, event types, metrics, logs, and recovery responsibilities, with explicit exceptions for any cross-owner writes. | Must | V-SL-BND-018 |
| SL-BND-019 | L2 | SL-BND-004, SL-BND-005 | Cross-service read contract | Cross-service reads shall use repository/query surfaces or API contracts and preserve read-only boundaries for services not owning the table or state. | Must | V-SL-BND-019 |
| SL-BND-020 | L2 | SL-BND-006, SL-BND-007 | Command handoff contract | Operator commands shall be accepted by API, persisted before asynchronous execution, expose command status, and be executed by the owning service without dashboard direct mutation. | Must | V-SL-BND-020 |
| SL-BND-021 | L2 | SL-BND-008, SL-BND-009, SL-BND-010 | Event handoff contract | Event-producing services shall persist outbox rows before publication, and event-consuming services shall persist offsets or idempotency observations before acknowledging work. | Must | V-SL-BND-021 |
| SL-BND-022 | L2 | SL-BND-011, SL-BND-012, SL-BND-013, SL-BND-017 | Boundary failure and reconciliation contract | Boundary failures shall define detection point, owner, retryability, reconciliation action, log event, metric, and operator-visible message. | Must | V-SL-BND-022 |

## Acceptance Criteria

The requirement is accepted when service boundary review proves each active service owns only the responsibilities listed here, the dashboard can complete the demo through FastAPI only, worker services can resume after restart using PostgreSQL state plus broker offsets, and no mutation path bypasses the documented control plane.
