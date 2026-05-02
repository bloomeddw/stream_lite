# WORKLOG-20260425-decision-closure-boundaries-contracts

## Summary

Closed the prior open MVP recommendations by converting them into numbered design decisions and requirements-backed behavior. Performed a second ambiguity pass focused on deferred profiles, retry eligibility, dashboard configuration storage, Sphinx scope, API control-plane contracts, system boundaries, and data contracts.

## Files Changed

- `stream_lite/docs/design/DEC-003-mvp-broker-profile.md`
- `stream_lite/docs/design/DEC-004-mvp-processing-engine.md`
- `stream_lite/docs/design/DEC-005-quarantine-file-handling.md`
- `stream_lite/docs/design/DEC-006-manual-retry-eligibility.md`
- `stream_lite/docs/design/DEC-007-dashboard-configuration-storage.md`
- `stream_lite/docs/design/DEC-008-sphinx-documentation-scope.md`
- `stream_lite/docs/design/INDEX.md`
- `stream_lite/docs/design/OPEN_DECISIONS.md`
- `stream_lite/docs/master_overview.md`
- `stream_lite/docs/reqs/CURRENT_REQUIREMENTS_RECAP.md`
- `stream_lite/docs/reqs/INDEX.md`
- `stream_lite/docs/reqs/REQ-001-runtime-and-deployment.md`
- `stream_lite/docs/reqs/REQ-003-file-detection-and-ingestion.md`
- `stream_lite/docs/reqs/REQ-004-file-validation-and-quarantine.md`
- `stream_lite/docs/reqs/REQ-005-event-streaming.md`
- `stream_lite/docs/reqs/REQ-006-job-metadata-and-state.md`
- `stream_lite/docs/reqs/REQ-007-processing-engine-spark-flink.md`
- `stream_lite/docs/reqs/REQ-009-retry-and-recovery.md`
- `stream_lite/docs/reqs/REQ-010-fastapi-control-plane.md`
- `stream_lite/docs/reqs/REQ-011-streamlit-command-center.md`
- `stream_lite/docs/reqs/REQ-012-operational-logging-and-observability.md`
- `stream_lite/docs/reqs/REQ-013-security-and-path-safety.md`
- `stream_lite/docs/reqs/REQ-014-verification-and-acceptance.md`
- `stream_lite/docs/reqs/REQ-015-system-boundaries-and-service-ownership.md`
- `stream_lite/docs/reqs/REQ-016-data-contracts-and-schema-governance.md`
- `stream_lite/docs/worklogs/WORKLOG-20260425-decision-closure-boundaries-contracts.md`

## Requirements Affected

- REQ-001: Runtime and Deployment
- REQ-003: File Detection and Ingestion
- REQ-004: File Validation and Quarantine
- REQ-005: Event Streaming
- REQ-006: Job Metadata and State
- REQ-007: Processing Engine
- REQ-009: Retry and Recovery
- REQ-010: FastAPI Control Plane
- REQ-011: Streamlit Command Center
- REQ-012: Operational Logging and Observability
- REQ-013: Security and Path Safety
- REQ-014: Verification and Acceptance
- REQ-015: System Boundaries and Service Ownership
- REQ-016: Data Contracts and Schema Governance

## Decisions Applied

| Decision | Applied requirement direction |
|---|---|
| DEC-003 | Redis Streams is the only active v0.1 broker profile; Redpanda is deferred. |
| DEC-004 | Spark is the only active v0.1 processing engine; Flink is deferred. |
| DEC-005 | Quarantine copies invalid files and preserves source files unchanged. |
| DEC-006 | Manual retry is allowed for eligible failed processing/delivery jobs and blocked for validation-policy quarantine failures. |
| DEC-007 | Dashboard presentation defaults are versioned YAML exposed through a read-only API endpoint. |
| DEC-008 | Static Sphinx docs are required first; autodoc is deferred until code modules exist. |

## Ambiguity Pass Results

- Clarified that deferred broker/engine profile selection fails startup with `CONFIG_UNSUPPORTED_DEFERRED_PROFILE`.
- Replaced vague Spark/Flink and Redis/Redpanda wording with active v0.1 scope plus future-compatible deferred scope.
- Replaced duplicate lowercase validation reason-code table with the uppercase deterministic code table.
- Clarified manual retry eligibility by state, stage, failure code, required operator reason, and API result.
- Clarified recursive watch behavior by watcher schema field and v0.1 rejection behavior.
- Clarified API endpoint contracts with request schemas, response schemas, status codes, errors, idempotency, timeout targets, log events, and metrics.
- Defined operator-safe message behavior in REQ-013.

## Boundary and Contract Additions

- Added REQ-015 to prevent implementation from blending dashboard, API, watcher, validation, worker, delivery, PostgreSQL, Redis Streams, source folder, destination folder, and quarantine responsibilities.
- Added REQ-016 to require named, versioned contracts before implementing API schemas, event schemas, logical database models, output manifests, quarantine records, dashboard presentation YAML, and verification evidence.

## Tests and Verification Performed

Documentation checks performed:

- Compared patched docs against the input zip to identify changed and new files.
- Checked active requirement rows for duplicate `SL-*` and `V-SL-*` definition rows; no duplicate definition rows were found.
- Ran a targeted ambiguity grep for subjective terms in requirement rows. Remaining matches are either the REQ-000 rule text itself or defined compound terms such as `operator-safe`, which is now defined in REQ-013.
- Confirmed `docs/design/OPEN_DECISIONS.md` now states no blocking design decisions remain for v0.1 implementation.

No application tests were run because this patch changes documentation only and does not add implementation code.

## Assumptions

- The requested recommendations were intended to become accepted v0.1 decisions rather than remain open questions.
- Redis Streams + Spark is the intended default local demo baseline.
- Future Redpanda, Flink, saved dashboard presentation mutation, authentication/roles, and validation reprocess workflows remain deferred until new decisions and requirements are added.

## Gaps Remaining

The active requirements now specify that the following supporting artifacts must be created before implementation of their surfaces:

- `.env.example` and `docs/operations/environment_variables.md`
- `docs/api/` endpoint schema files or `stream_lite/schemas/api/`
- `docs/schemas/events/` or `stream_lite/schemas/events/`
- `docs/operations/prometheus_metrics.md`
- `docs/operations/retry_policy.md`, `fault_tolerance.md`, and `quarantine_policy.md`
- `docs/verification/verification_matrix.md`, `acceptance_test_plan.md`, and `evidence_index.md`

These are not blocking design decisions; they are requirements-backed documentation tasks before coding the corresponding surfaces.

## Rollback Notes

Rollback by removing DEC-003 through DEC-008, REQ-015, REQ-016, this worklog, and reverting the modified requirement/index/overview files to the prior zip baseline.

## Next Step

Create the supporting contract artifacts required by REQ-016 and REQ-000 before implementation begins: API schema docs, event schemas, environment variable catalog, metrics catalog, and verification matrix.
