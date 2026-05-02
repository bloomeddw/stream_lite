# Stream Lite Master Overview

## Document Control

| Field | Value |
|---|---|
| Product | Stream Lite |
| Document type | Product demo overview, intent, and high-level architecture design |
| Version | 0.1.0 |
| Status | Draft requirements baseline |
| Audience | Founder, product owner, engineer, evaluator, future implementation agent |
| Scope | Dockerized event-driven file ingestion platform with FastAPI API, PostgreSQL metadata store, Redis Streams eventing, Streamlit command center, and Spark proof-of-concept processing |

## Product Demo Intent

Stream Lite is a local-first, Dockerized proof-of-concept for an event-driven file ingestion platform. The demo should show a user opening a Streamlit dashboard, selecting one or more source folders to watch, selecting one or more destination folders or output zones, starting a watch session, dropping files into a watched folder, and seeing file validation, job creation, processing state, retry behavior, operational logs, and processed outputs reflected through the dashboard and API.

The system is intentionally built as a miniature data platform rather than a simple folder-copy script. It should demonstrate the same core ideas found in larger production systems: explicit contracts, durable job metadata, event streams, observable state transitions, retry handling, idempotency, validation, and clear separation between operational control data and processed analytical outputs.

## Public Repository Demo Methodology

The public repository shall be understandable before it is executable. A reader should be able to inspect the requirements, architecture overview, interface contracts, verification plan, and worklogs to understand the design methodology without running the stack. A user who downloads and runs the project should then be able to verify the same behavior through Docker Compose, API responses, Streamlit screens, logs, metrics, event evidence, and filesystem outputs.

The documentation shall separate demo/MVP scope from future enhancements so external evaluators can distinguish intentional architectural trade-offs from missing implementation work.

## Business and Technical Positioning

The purpose of this proof-of-concept is to demonstrate data platform engineering judgment. It should show that the builder can design a system around events, contracts, observability, and controlled execution rather than ad hoc scripts. The goal is not to overbuild a distributed platform before the use case is validated. The goal is to make the product demo credible, inspectable, and extendable.

The architecture follows the data-intensive system principle that different workloads have different access patterns. Operational state such as job status, retry count, and user-selected folder configuration belongs in a low-latency operational store such as PostgreSQL. Derived outputs, processed files, and later analytical datasets belong in file/object storage or a lake-style layout. Event streams coordinate change between services and enable asynchronous processing.

## Demo User Story

As an operator, I want to select one or more folders to watch, select where processed outputs should be delivered, and monitor each ingestion job from detection through validation, processing, delivery, retry, failure, or completion, so that I can trust the system to move and transform incoming files without losing track of operational state.

## High-Level Architecture

```text
+----------------------+       +-------------------+       +-----------------------+
| Streamlit Dashboard  | <---> | FastAPI Control   | <---> | PostgreSQL Metadata   |
| Command Center       | REST  | Plane API         | SQL   | Jobs, Watchers, Logs  |
+----------------------+       +---------+---------+       +-----------------------+
                                      |
                                      | publish / consume events
                                      v
                              +---------------+
                              | Redis Streams |
                              | v0.1 broker  |
                              +-------+-------+
                                      |
        +-----------------------------+-----------------------------+
        |                                                           |
        v                                                           v
+-------------------+                                      +----------------------+
| Directory Watcher |                                      | Processing Worker    |
| File Detection    |                                      | Spark/Flink POC      |
+---------+---------+                                      +----------+-----------+
          |                                                           |
          v                                                           v
+-------------------+                                      +----------------------+
| Validation Service|                                      | Delivery Service     |
| File Contracts    |                                      | Output Transfer      |
+-------------------+                                      +----------------------+
```

## System Planes

### 1. Command Plane

The Streamlit dashboard and FastAPI API form the command plane. This plane lets the operator create folder watchers, configure source and destination paths, start or stop watchers, inspect job state, retry failed jobs, and view operational logs.

### 2. Event Plane

Redis Streams carries durable processing events between v0.1 components. Redpanda is deferred future scope and requires a new decision record, requirements update, and verification evidence before it can be selected at runtime.

### 3. Metadata Plane

PostgreSQL stores watcher configuration, job metadata, file fingerprints, event offsets where applicable, validation outcomes, processing attempts, delivery attempts, and operational audit logs.

### 4. Processing Plane

Spark processes validated files in v0.1. Flink is deferred future scope and requires a new decision record, requirements update, and verification evidence before it can be selected at runtime.

### 5. Storage and Delivery Plane

The file system is used for local source and destination folders. Processed outputs shall use deterministic job-scoped paths. Invalid files shall be copied to quarantine with an explicit quarantine locator while preserving source files unchanged. Object storage migration is future scope and requires new requirements.

## Recommended Proof-of-Concept Choice

For v0.1, Apache Spark is the accepted processing engine. Flink remains future-compatible scope only and shall not be implemented until a later decision activates a streaming-oriented version.

## Core Capabilities

| Capability | Requirement document |
|---|---|
| Dockerized runtime and configuration | `reqs/REQ-001-runtime-and-deployment.md` |
| Source and destination folder management | `reqs/REQ-002-folder-watch-management.md` |
| File detection and ingestion | `reqs/REQ-003-file-detection-and-ingestion.md` |
| File validation and quarantine | `reqs/REQ-004-file-validation-and-quarantine.md` |
| Event streaming and messaging | `reqs/REQ-005-event-streaming.md` |
| Job metadata and state model | `reqs/REQ-006-job-metadata-and-state.md` |
| Processing engine with Spark MVP and future Flink profile | `reqs/REQ-007-processing-engine-spark-flink.md` |
| Output delivery and transfer | `reqs/REQ-008-output-delivery.md` |
| Retry handling and failure recovery | `reqs/REQ-009-retry-and-recovery.md` |
| FastAPI control plane | `reqs/REQ-010-fastapi-control-plane.md` |
| Streamlit command center | `reqs/REQ-011-streamlit-command-center.md` |
| Operational logging and observability | `reqs/REQ-012-operational-logging-and-observability.md` |
| Security, path safety, and operator guardrails | `reqs/REQ-013-security-and-path-safety.md` |
| Verification and acceptance | `reqs/REQ-014-verification-and-acceptance.md` |
| System boundaries and service ownership | `reqs/REQ-015-system-boundaries-and-service-ownership.md` |
| Data contracts and schema governance | `reqs/REQ-016-data-contracts-and-schema-governance.md` |
| End-to-end lifecycle and handoff orchestration | `reqs/REQ-017-end-to-end-lifecycle-and-handoff-orchestration.md` |

## Key Demo Metrics

| Metric | v0.1 target |
|---|---:|
| File detection latency, p95 | <= 2 seconds after stable file write |
| API read latency, p95 | <= 300 ms for dashboard endpoints with <= 10,000 jobs |
| Job metadata write success rate | >= 99.5% in local demo runs |
| Valid file processing success rate | >= 99% for supported test fixtures |
| Invalid file quarantine accuracy | 100% for defined invalid fixture set |
| Duplicate-file suppression | 100% for same path + size + content hash fixture set |
| Retry attempts per retryable failure | configurable, default 3 |
| Event publish latency, p95 | <= 500 ms from state transition to event append |
| Dashboard refresh interval | configurable, default 2 seconds |
| Structured log coverage | 100% of state transitions emit structured logs |
| End-to-end demo throughput | >= 100 small files/minute on local developer machine |

## Major State Model

```text
DETECTED -> STABILIZING -> REGISTERED -> VALIDATING -> VALIDATED
VALIDATED -> PROCESSING -> PROCESSED -> DELIVERING -> DELIVERED -> COMPLETED
VALIDATING -> INVALID -> QUARANTINED
PROCESSING|DELIVERING -> RETRY_PENDING -> PROCESSING|DELIVERING
PROCESSING|DELIVERING|VALIDATING -> FAILED
```

Every job shall have exactly one current state and a state-transition history. A terminal state shall be one of `COMPLETED`, `COMPLETED_WITH_DELIVERY_ERRORS`, `FAILED`, or `QUARANTINED`.

## Non-Goals for v0.1

- Multi-tenant authentication and role-based access control beyond local operator guardrails.
- Cloud deployment automation.
- Kubernetes orchestration.
- Exactly-once distributed processing guarantees across all failure modes.
- Full data lakehouse implementation.
- Arbitrary user-authored Spark or Flink code from the dashboard.

## Architectural Assumptions

- The system runs locally through Docker Compose.
- PostgreSQL is the source of truth for operational job state.
- Redis Streams is the v0.1 event coordination mechanism; Redpanda is deferred future scope.
- Local file system folders are the v0.1 source and destination stores.
- Spark runs inside Docker as the v0.1 proof-of-concept processing service; Flink is deferred future scope.
- The dashboard is an operator interface, not the source of truth.
- All active requirements shall be verifiable by logs, API responses, database records, filesystem artifacts, and fixture-based tests.

## Traceability Convention

Each requirement uses this ID pattern:

```text
SL-<CAPABILITY>-<NUMBER>
```

Each verification case uses this ID pattern:

```text
V-SL-<CAPABILITY>-<NUMBER>
```

Evidence should be stored under:

```text
stream_lite/docs/verification/<verification_id>/
```

Minimum evidence artifacts:

- `case_manifest.json`
- `inputs/`
- `actual/`
- `expected/`
- `comparison.json`
- `summary.md`

## Accepted Baseline Decisions

| Decision | Options Considered | Accepted v0.1 Direction |
|---|---|---|
| Event broker | Redis Streams, Redpanda | Redis Streams is accepted for v0.1; Redpanda is deferred until a later decision activates Kafka-compatible verification. |
| Processing engine | Spark, Flink | Spark is accepted for v0.1 file processing demo; Flink is deferred until a later decision activates streaming verification. |
| File stability rule | time-based, size/hash-based, atomic rename only | accepted: stable size for 2 consecutive checks over >= 1 second; atomic rename is allowed as an operator habit but not required for detection. |
| Output layout | flat destination, job-scoped destination, dataset-style destination | job-scoped destination for v0.1, dataset-style later |
| User path selection | manual text input, browser-style picker, mounted folder registry | mounted folder registry with validated text input fallback |

## 2026-04-25 Requirement Addition: Idle Watchers and Folder Health

A started watcher may be healthy and idle when no files are present. It becomes active only after a stable source file is available and a reachable destination is assigned. The operator command center shall show source and destination health with green, yellow, and red dots so reviewers can distinguish a stable idle system from a blocked transfer. Source and destination folders can be typed into filepath boxes or selected through API-backed browse-folder controls in Streamlit.

## Recent Requirement Direction: Tag-Based Routing

The MVP multi-source and multi-destination routing method is `tag_match_all_destinations`. Each source and destination folder can be assigned semicolon-delimited route tags. The system normalizes the tags and delivers accepted files to every destination sharing at least one tag with the source. This keeps routing easy to explain in a public demo while still proving one-to-one, one-to-many, many-to-one, and many-to-many behavior.

## Recent Requirement Direction: Centralized Dashboard Presentation

The Streamlit command center shall load dashboard color scheme and layout behavior from centralized presentation configuration. Health states remain semantic: stable/green, warning/yellow, and faulty/red. Layout profiles shall control section order, visibility, and grouping so reviewer and operator views can evolve without duplicating styling constants across pages.

## Decision status before implementation

The prior open MVP recommendations are now accepted and captured in `docs/design/DEC-003-*` through `DEC-008-*`. No blocking design decisions remain for requirements-first implementation of the default Redis Streams + Spark local demo. Future activation of Redpanda, Flink, saved dashboard presentation settings, validation reprocess workflows, or authentication/roles requires a new decision record and requirement update before code changes.

## Recent Requirement Direction: Boundaries and Data Contracts

The requirements now explicitly separate command-plane, event-plane, metadata-plane, processing-plane, storage/delivery-plane, and observability-plane responsibilities. The dashboard mutates system state only through FastAPI. PostgreSQL is the source of truth for operational state. Redis Streams coordinates work but is not the source of truth. Spark processing, validation, and delivery side effects are owned by worker services rather than API request handlers.

The requirements now also define schema governance before implementation. API payloads, event messages, PostgreSQL logical tables, output manifests, quarantine records, dashboard presentation YAML, and verification evidence require named, versioned contracts before code is written.

## Recent Requirement Direction: Lifecycle Handoffs and Readiness

The requirements now define the end-to-end lifecycle as durable handoffs rather than implicit service behavior. Job-scoped events require a persisted job ID first, lifecycle events are published through a PostgreSQL-backed event outbox, asynchronous control-plane commands have durable command status, duplicate file arrivals are suppressed before new job creation, and worker stages use durable ownership claims plus reconciliation to recover after restart.

The current baseline is ready for implementation planning, but code generation remains gated by contract artifacts: API schemas, event schemas, logical database model, environment variable catalog, retry/fault/quarantine policies, metrics catalog, verification matrix, and Sphinx static skeleton.

## 2026-04-25 Contract Decomposition Baseline

The requirements baseline now includes implementation-facing contract artifacts for API endpoints, API schemas, event schemas, artifact schemas, logical data model, environment variables, Prometheus metrics, retry/fault/quarantine policies, Streamlit control mapping, and verification evidence. These artifacts are intended to be read before implementation planning so service responsibilities and handoffs are explicit instead of inferred from prose requirements.

The current recommendation is to proceed to an implementation plan using the owning requirements plus their contract artifacts: API endpoints and schemas, event schemas, logical database model, environment catalog, metrics catalog, Streamlit control matrix, retry/fault/quarantine policies, verification matrix, and Sphinx static build scope.
