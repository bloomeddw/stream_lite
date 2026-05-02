# Current Requirements Recap

## Purpose Captured

Stream Lite is currently documented as a public, local-first demonstration of data platform architecture and design methodology. The requirements show how a small Dockerized file-ingestion system can be specified using explicit contracts, measurable acceptance criteria, event-driven coordination, durable operational metadata, retry behavior, observability, and verification evidence.

The documented demo is intended to let users clone or download the repository, read the architecture and requirements, start the platform locally, drop test files into watched folders, and observe detection, validation, processing, delivery, retry/failure handling, logs, metrics, API state, and dashboard behavior.

## Active Requirement Baseline

| Requirement | Capability | What is currently captured |
|---|---|---|
| REQ-001 | Runtime and Deployment | Docker Compose runtime, service exposure, mounted folders, PostgreSQL persistence, broker selection, health checks, environment-driven configuration, startup readiness, reset procedure, stable service/volume names, and service log access. |
| REQ-002 | Folder Watch Management | Source and destination folder configuration, watcher lifecycle behavior, tag-based routing policy, path validation, multi-folder support, and watcher-related acceptance criteria. |
| REQ-003 | File Detection and Ingestion | File discovery, stability checks, duplicate suppression, registration, ingestion latency targets, and job creation expectations. |
| REQ-004 | File Validation and Quarantine | Validation dimensions, invalid-file handling, quarantine behavior, reason codes, validation metrics, and quarantine acceptance criteria. |
| REQ-005 | Event Streaming | Redis Streams or Redpanda positioning, required event types, event payload expectations, publish/consume behavior, event latency targets, and event acceptance criteria. |
| REQ-006 | Job Metadata and State | PostgreSQL-backed operational source of truth, job identity, state model, state transition history, attempts, retry schedules, query/filter behavior, restart recovery, and invalid transition rejection. |
| REQ-007 | Processing Engine and Orchestration | Spark/Flink processing contract, default demo processing outputs, processing summary, state transitions, engine adapter consistency, worker job claiming, concurrency, graceful shutdown, checksums, output manifests, and processing failure events. |
| REQ-008 | Output Delivery | Job-scoped output delivery, tag-resolved destination handling, delivery attempts, per-destination outcomes, output layout, delivery state transitions, and delivery acceptance criteria. |
| REQ-009 | Retry and Recovery | Retryable failure classification, retry attempts, backoff behavior, terminal failure behavior, recovery expectations, and retry acceptance criteria. |
| REQ-010 | FastAPI Control Plane | Health, watcher, job, retry, metrics summary, and log endpoints; request validation; filtering; pagination; stable error responses; and OpenAPI expectations. |
| REQ-011 | Streamlit Command Center | Operator dashboard requirements for health, folders, route tags, route preview, centralized theme/layout configuration, jobs, events, validation failures, quarantine, retries, outputs, metrics, and safe operational controls. |
| REQ-012 | Operational Logging and Observability | Structured logging expectations, Prometheus metric coverage, metric naming conventions, state transition logging, dashboard metric use, and observability acceptance criteria. |
| REQ-013 | Security and Path Safety | Local-demo guardrails, path allowlisting, safe path display, secret handling, arbitrary-path prevention, and operator safety controls. |
| REQ-014 | Verification and Acceptance | Verification philosophy, evidence artifacts, acceptance test planning, requirement closure expectations, and demo-level validation coverage. |

## Cleanup Performed

Two duplicate draft requirement files were mixed into the active baseline:

- `REQ-006-processing-orchestration.md`
- `REQ-012-dockerized-runtime.md`

They were removed from the active patch. Unique processing orchestration content was migrated into `REQ-007-processing-engine-spark-flink.md`. Unique Docker runtime content was migrated into `REQ-001-runtime-and-deployment.md`. The requirements index now has one active file per requirement number.

## Current Strengths

The requirement set already captures the major architectural planes of the demo: command plane, event plane, metadata plane, processing plane, storage/delivery plane, and observability plane. It also captures a clear traceability model using `SL-*` requirement IDs, `V-SL-*` verification IDs, measurable targets, and evidence artifacts.

The public-demo story is coherent: the reader can understand why Stream Lite is more than a folder-copy script, what each service is responsible for, what behavior is measurable, and how correctness will be proven.

## Known Gaps to Address Next

The current docs are a strong baseline, but the following areas should be tightened before implementation or public release:

| Gap | Recommended next action |
|---|---|
| Environment variables are referenced but not yet fully enumerated. | Create `stream_lite/.env.example` and `docs/operations/environment_variables.md` with owner, defaults, allowed values, sensitivity, failure behavior, and related requirement IDs. |
| API endpoints are listed but not fully specified per route. | Create `docs/api/` route specs grouped by `/health`, `/watchers`, `/jobs`, `/events`, `/files`, `/outputs`, `/config`, and `/operations`. |
| Event schemas are described but not yet formalized as versioned schemas. | Create `docs/schemas/` or `schemas/` event schema files with producers, consumers, fields, compatibility, dead-letter behavior, and related requirements. |
| Retry, quarantine, and fault behavior need consolidated operator-facing policy docs. | Create or expand `docs/operations/retry_policy.md`, `fault_tolerance.md`, and `quarantine_policy.md`. |
| Metrics are required but not yet fully inventoried. | Create `docs/operations/prometheus_metrics.md` with metric name, type, labels, owner, trigger, threshold, and requirement IDs. |
| Streamlit controls need direct endpoint and state-transition mapping. | Add a dashboard control matrix mapping each UI control to API route, requirement ID, validation rule, log, metric, and success/failure behavior. |
| Verification IDs exist but need a full closure matrix. | Create or expand `docs/verification/verification_matrix.md`, `acceptance_test_plan.md`, and `evidence_index.md`. |
| Sphinx automation is referenced in project goals but not yet requirements-backed in detail. | Add Sphinx documentation requirements or a dedicated docs automation requirement section with build command, failure behavior, and coverage expectations. |

## Recommended Next Requirement Pass

The next pass should convert the known gaps into requirements-backed supporting docs before implementation starts. The highest-value order is: environment variables, API route contracts, event schemas, fault/retry/quarantine policies, metrics catalog, Streamlit control matrix, and verification matrix.

## Recent Addition: Idle Watchers and Folder Health

The baseline now captures that a configured watcher can remain idle when no source files are present, then become active when a stable file arrives and a reachable destination is assigned. Source and destination folders now have explicit health semantics: green for stable/usable, yellow for warning or pending/degraded conditions, and red for blocking faults. Streamlit is required to show colored dots next to each source and destination folder, provide filepath boxes, expose browse-folder controls backed by the API, and allow folder additions without editing configuration files or restarting services.

The affected requirement areas are folder watch management, file detection, output delivery, FastAPI, Streamlit, observability, and verification. These additions strengthen the demo by making operator readiness and transfer blocking conditions visible before, during, and after file processing.

## Recent Addition: Tag-Based Folder Routing and Dashboard Presentation Configuration

The baseline now captures tag-based many-to-many folder routing as the MVP multi-source and multi-destination strategy. Operators assign semicolon-delimited route tags to each source and destination folder. The system trims, uppercases, validates, and deduplicates those tags, then routes accepted source files to every destination sharing at least one normalized tag. This supports one-to-one, one-to-many, many-to-one, and many-to-many delivery without a complex rule engine.

The baseline also captures centralized Streamlit presentation configuration. Dashboard colors shall come from semantic theme tokens, including stable/green, warning/yellow, and faulty/red health indicators. Dashboard layout shall come from layout profiles that control section order, visibility, and grouping. The goal is to let the public demo change styling and layout in one place while preserving the meaning of operational health states.

## Requirements quality pass on 2026-04-25

This pass added `REQ-000` to control ambiguity, tightened retry defaults, clarified MVP tag routing, made route-tag limits and error codes explicit, specified validation/quarantine behavior for local demo profiles, added event ordering and dead-letter contracts, strengthened job state and delivery partial-failure semantics, added API response/idempotency rules, clarified Streamlit control-to-API behavior, and introduced `docs/design/OPEN_DECISIONS.md` for decisions that should be answered before implementation.

## 2026-04-25 Decision Closure and Second Ambiguity Pass

The prior open recommendations are now requirements-backed accepted v0.1 decisions:

| Topic | Accepted v0.1 requirement direction |
|---|---|
| Broker profile | Redis Streams is the only active v0.1 broker; Redpanda is deferred and rejected at startup with `CONFIG_UNSUPPORTED_DEFERRED_PROFILE`. |
| Processing engine | Spark is the only active v0.1 processing engine; Flink is deferred and rejected at startup with `CONFIG_UNSUPPORTED_DEFERRED_PROFILE`. |
| Quarantine handling | Invalid files are copied to quarantine; source files are not deleted, moved, renamed, or modified. |
| Manual retry eligibility | Eligible failed processing and delivery jobs may be manually retried; validation-policy quarantine failures are blocked with `409 JOB_NOT_RETRYABLE`. |
| Dashboard configuration storage | Dashboard presentation defaults are stored in versioned YAML and exposed through read-only `GET /config/dashboard-presentation`; persisted presentation mutation is deferred. |
| Sphinx scope | v0.1 requires static Sphinx docs first; Python autodoc is deferred until code modules exist. |

The second ambiguity pass added explicit startup rejection behavior for deferred profiles, API endpoint schemas/status codes/idempotency/log/metric expectations, manual retry eligibility cases, dashboard presentation fallback behavior, Sphinx static-first behavior, and recursive watcher deferral behavior.

## 2026-04-25 System Boundary and Data Contract Additions

Two active requirement documents were added:

| Requirement | Purpose |
|---|---|
| `REQ-015-system-boundaries-and-service-ownership.md` | Defines ownership boundaries across Streamlit, FastAPI, watcher, validation, worker, delivery, PostgreSQL, Redis Streams, source folders, destination folders, and quarantine folders. |
| `REQ-016-data-contracts-and-schema-governance.md` | Defines schema governance for API contracts, event schemas, logical database models, manifests, quarantine records, dashboard presentation YAML, and verification evidence. |

No blocking open decisions remain for requirements-first implementation of the Redis Streams + Spark v0.1 local demo. Deferred future decisions are listed in `docs/design/OPEN_DECISIONS.md` and require new decision records before implementation.
