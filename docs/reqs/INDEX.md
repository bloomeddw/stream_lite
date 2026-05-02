# Requirements Index

This index lists the active Stream Lite requirement baseline. Duplicate draft files from the mixed requirement versions were removed, and unique requirements were migrated into the active capability files using the `SL-<CAPABILITY>-<NUMBER>` ID convention.

## Documentation tree

```{toctree}
:maxdepth: 1

CURRENT_REQUIREMENTS_RECAP
REQ-000-requirements-quality-and-ambiguity-control
REQ-001-runtime-and-deployment
REQ-002-folder-watch-management
REQ-003-file-detection-and-ingestion
REQ-004-file-validation-and-quarantine
REQ-005-event-streaming
REQ-006-job-metadata-and-state
REQ-007-processing-engine-spark-flink
REQ-008-output-delivery
REQ-009-retry-and-recovery
REQ-010-fastapi-control-plane
REQ-011-streamlit-command-center
REQ-012-operational-logging-and-observability
REQ-013-security-and-path-safety
REQ-014-verification-and-acceptance
REQ-015-system-boundaries-and-service-ownership
REQ-016-data-contracts-and-schema-governance
REQ-017-end-to-end-lifecycle-and-handoff-orchestration
REQUIREMENT_REFERENCE_INVENTORY
```

| ID | Capability | File | Status |
|---|---|---|---|
| REQ-000 | Requirements Quality and Ambiguity Control | `REQ-000-requirements-quality-and-ambiguity-control.md` | Active |
| REQ-001 | Runtime and Deployment | `REQ-001-runtime-and-deployment.md` | Active |
| REQ-002 | Folder Watch Management | `REQ-002-folder-watch-management.md` | Active |
| REQ-003 | File Detection and Ingestion | `REQ-003-file-detection-and-ingestion.md` | Active |
| REQ-004 | File Validation and Quarantine | `REQ-004-file-validation-and-quarantine.md` | Active |
| REQ-005 | Event Streaming | `REQ-005-event-streaming.md` | Active |
| REQ-006 | Job Metadata and State | `REQ-006-job-metadata-and-state.md` | Active |
| REQ-007 | Processing Engine and Orchestration | `REQ-007-processing-engine-spark-flink.md` | Active; includes migrated processing orchestration requirements |
| REQ-008 | Output Delivery | `REQ-008-output-delivery.md` | Active |
| REQ-009 | Retry and Recovery | `REQ-009-retry-and-recovery.md` | Active |
| REQ-010 | FastAPI Control Plane | `REQ-010-fastapi-control-plane.md` | Active |
| REQ-011 | Streamlit Command Center | `REQ-011-streamlit-command-center.md` | Active |
| REQ-012 | Operational Logging and Observability | `REQ-012-operational-logging-and-observability.md` | Active |
| REQ-013 | Security and Path Safety | `REQ-013-security-and-path-safety.md` | Active |
| REQ-014 | Verification and Acceptance | `REQ-014-verification-and-acceptance.md` | Active |
| REQ-015 | System Boundaries and Service Ownership | `REQ-015-system-boundaries-and-service-ownership.md` | Active |
| REQ-016 | Data Contracts and Schema Governance | `REQ-016-data-contracts-and-schema-governance.md` | Active |
| REQ-017 | End-to-End Lifecycle and Handoff Orchestration | `REQ-017-end-to-end-lifecycle-and-handoff-orchestration.md` | Active |

## Removed Duplicate Drafts

| Removed file | Reason | Disposition |
|---|---|---|
| `REQ-006-processing-orchestration.md` | Duplicate `REQ-006` number conflicted with Job Metadata and State. | Unique orchestration requirements migrated into `REQ-007-processing-engine-spark-flink.md`. |
| `REQ-012-dockerized-runtime.md` | Duplicate `REQ-012` number conflicted with Operational Logging and Observability and overlapped Runtime and Deployment. | Unique Docker runtime requirements migrated into `REQ-001-runtime-and-deployment.md`. |

## 2026-04-25 Folder Idle and Health Indicator Additions

The current baseline now includes requirements for idle watcher behavior, dashboard source/destination folder browsing, filepath entry controls, source and destination health indicators, and green/yellow/red dashboard status dots. The primary affected files are `REQ-002`, `REQ-003`, `REQ-008`, `REQ-010`, `REQ-011`, `REQ-012`, and `REQ-014`.

## 2026-04-25 Tag-Based Multi-Source/Multi-Destination Routing Additions

The current baseline now defines `tag_match_all_destinations` as the default MVP routing policy. Operators assign semicolon-delimited route tags to source and destination folders, the system normalizes those tags, and a source file is delivered to every destination sharing at least one normalized tag. The baseline also adds route preview behavior, unmatched folder warnings, per-destination delivery outcomes, and verification coverage for one-to-one, one-to-many, many-to-one, and many-to-many routing.

## 2026-04-25 Centralized Streamlit Presentation Configuration Additions

The current baseline now requires Streamlit dashboard colors and layout to be controlled through centralized presentation configuration. Theme tokens define status colors and other semantic colors, while layout profiles define section ordering, visibility, and grouping. Individual dashboard sections shall consume the centralized configuration instead of hardcoding display values.

## Previous Numbering Rule

This section was superseded by the current numbering rule update below after `REQ-015` and `REQ-016` were added.

## 2026-04-25 Decision Closure, Boundary, and Contract Additions

The current baseline now accepts the prior open recommendations as v0.1 decisions: Redis Streams only, Spark only, copy-based quarantine, constrained manual retry eligibility, YAML-backed dashboard presentation configuration, and static-first Sphinx documentation. `REQ-015` defines service ownership and system boundaries. `REQ-016` defines data contract and schema governance requirements for API payloads, events, database logical models, artifacts, dashboard presentation configuration, and verification evidence.

## Current Numbering Rule Update

- `REQ-001` through `REQ-017` are active capability documents. Decomposed contracts are maintained inside their owning requirement files and supporting docs, not in a separate meta-requirement.
- `REQ-000` controls requirements quality and ambiguity.
- Individual requirements use stable `SL-*` IDs inside each document.
- Verification cases use stable `V-SL-*` IDs and shall be mapped in the verification matrix before implementation.

## 2026-04-25 Lifecycle and Handoff Orchestration Additions

The current baseline now closes end-to-end lifecycle gaps by requiring job ID allocation before job-scoped events, duplicate-suppression observations without duplicate jobs, transactional event outbox publication, durable command status, service reconciliation loops, stage ownership claims, and queue/backpressure visibility. `REQ-017` is the primary cross-component handoff contract and ties together watcher, validator, processor, delivery, retry scheduler, event dispatcher, API, Streamlit, PostgreSQL, and Redis Streams behavior.

## 2026-04-25 Contract Decomposition Additions

The current baseline includes implementation-facing decomposition artifacts for API endpoints, API schemas, event schemas, logical data model, environment variables, Prometheus metrics, retry/fault/quarantine policies, Streamlit controls, verification matrix, acceptance test plan, and evidence index. These artifacts are now traced to their owning requirements (`REQ-004`, `REQ-005`, `REQ-006`, `REQ-008`, `REQ-009`, `REQ-010`, `REQ-011`, `REQ-012`, `REQ-014`, `REQ-016`, and `REQ-017`) rather than a separate meta-requirement.

## 2026-04-25 API and Supporting Contract Traceability Cleanup

The current baseline now resolves stale or missing requirement references discovered from `docs/api/endpoints.md` and supporting contract catalogs. `GET /events` is requirements-backed by `SL-EVT-015`; manual retry endpoint traceability now points to the existing `SL-RET-*` retry requirements; quarantine catalog references are backed by `SL-VAL-016`; and delivery catalog references now use the active `SL-OUT-*` namespace instead of stale `SL-DEL-*` identifiers.


## 2026-04-25 Requirement Decomposition Level Model

The active baseline now uses three requirement levels:

- L1 capability requirements define system capability intent and acceptance at the owning `REQ-###.md` level.
- L2 contract requirements decompose L1 requirements into endpoints, schemas, events, states, retries, metrics, logs, environment variables, and other implementation-facing contracts.
- L3 implementation trace requirements decompose L2 contracts into named route handlers, functions, modules, command processors, validators, producers, consumers, and verification targets.

Existing capability files remain the L1 baseline. New decomposition work shall be added to the owning capability file, not a new standalone decomposition requirement file. Requirement references from docs outside `docs/reqs/` shall resolve to active IDs in the owning requirement file, excluding verification IDs that begin with `V-SL-`.

## 2026-04-25 REQ-018 Retirement

`REQ-018-contract-decomposition-and-implementation-readiness.md` is retired and shall be deleted from active baselines. Its `SL-DECOMP-*` readiness requirements are retained under `REQ-000` because they govern requirements quality and implementation readiness across capability files. Future decomposition shall happen in the owning capability files as L2/L3 rows rather than in a standalone decomposition requirement file.
