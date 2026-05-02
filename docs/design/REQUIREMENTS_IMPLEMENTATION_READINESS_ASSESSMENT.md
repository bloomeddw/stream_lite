# Requirements Implementation Readiness Assessment

## Assessment Date

2026-04-25

## Overall Readiness Estimate

The requirements baseline is approximately **82% complete for starting an implementation plan** and approximately **68% complete for beginning code generation without additional contract documents**.

This means implementation planning can start now, but coding should still be gated by the supporting contract documents listed below. The remaining work is decomposition and contract elaboration, not unresolved architecture direction.

## Why the Baseline Is Ready for Implementation Planning

The current requirements now define:

- v0.1 runtime profile: Docker Compose, Redis Streams, PostgreSQL, FastAPI, Streamlit, Spark.
- Accepted design decisions for broker, processor, quarantine behavior, retry eligibility, dashboard presentation storage, and Sphinx scope.
- Folder watcher lifecycle and tag-based multi-source/multi-destination routing.
- Job state model, terminal states, state history, and durable metadata ownership.
- File detection, stabilization, validation, quarantine, processing, delivery, retry, logging, metrics, path safety, and verification expectations.
- Service boundaries between dashboard, API, watcher, validator, processor, delivery, retry scheduler, event dispatcher, PostgreSQL, and Redis Streams.
- End-to-end handoff requirements tying components together through durable state, outbox events, command records, reconciliation, and idempotency.

## Gaps Closed in This Pass

| Prior gap | Resolution |
|---|---|
| Early file events required `job_id` but job ID allocation was not explicit. | REQ-003 and REQ-017 now require initial `DETECTED` job persistence before `file.detected`. |
| Duplicate behavior mixed quarantine and possible future skipped states. | Duplicates are now suppressed before job creation and recorded as duplicate-suppression observations. |
| Event publication could be lost between database commit and broker append. | REQ-005 now requires a transactional PostgreSQL `event_outbox` and dispatcher. |
| API accepted async commands but command status tracking was incomplete. | REQ-010, REQ-011, REQ-016, and REQ-017 now require command records and `GET /commands/{command_id}`. |
| Service-to-service handoffs were spread across individual requirements but lacked a single lifecycle matrix. | REQ-017 now defines the complete handoff matrix and reconciliation requirements. |
| Worker claim/recovery behavior was not tied to durable ownership records. | REQ-006, REQ-007, and REQ-016 now require stage ownership claims. |
| Backpressure behavior was implicit. | REQ-017 and REQ-012 now require worker concurrency limits and queue lag metrics. |
| Control-plane pause/stop/resume semantics were incomplete. | REQ-010 now defines pause, stop, resume, start, and idempotent command behavior. |

## Remaining Required Decomposition Before Coding

The following are not open design decisions, but they are required before implementation tasks should be assigned to Codex or another implementation agent:

| Area | Required artifact | Blocking for coding? | Reason |
|---|---|---:|---|
| API schemas | `docs/api/` or `stream_lite/schemas/api/` request/response contracts | Yes | Prevents route handler field-name drift and response ambiguity. |
| Event schemas | `docs/schemas/events/*.md` or JSON Schema files | Yes | Prevents producers/consumers from inventing incompatible payloads. |
| Logical database model | Table-level schema document or migration contract | Yes | Required for jobs, outbox, commands, attempts, offsets, and ownership claims. |
| Environment variable catalog | `.env.example` plus operations environment docs | Yes | Required by project rule before code uses env vars. |
| Retry/fault/quarantine policy docs | Operations policy files | Yes | Ensures failure paths and operator messages remain consistent. |
| Metrics catalog | Prometheus metric docs with labels and cardinality | Yes | Required before instrumentation implementation. |
| Verification matrix | Requirement-to-verification mapping | Yes | Needed to prove closure and drive test planning. |
| Sphinx skeleton | Static docs build config and index | No for planning; yes before docs acceptance | Required by accepted documentation scope. |

## Remaining Non-Blocking Enhancements

These can wait until after implementation planning begins:

- Persisted dashboard theme/layout preference mutation beyond session-local selection.
- Redpanda activation.
- Flink activation.
- Recursive folder watching.
- Reprocess/edit workflow for quarantined files.
- Job cancellation semantics.
- Object storage delivery profile.

## Recommendation

Proceed to an **implementation plan** next, but structure it as a contract-first plan with the first milestone dedicated to API schemas, event schemas, database logical model, environment variable catalog, metrics catalog, and verification matrix. Start coding only after those contracts are accepted.

## 2026-04-25 Decomposition Update

After folding the contract artifact set back into owning requirements, the baseline is approximately 92% complete for implementation planning and 82% complete for safe code generation. The remaining gap before code generation is not architecture direction; it is fixture-level detail and executable lint/test scaffolding.

### Newly Closed Decomposition Gaps

| Gap | Closure artifact |
|---|---|
| API route behavior and status codes were scattered across prose. | `docs/api/endpoints.md`, `docs/api/errors.md` |
| API request/response schemas were named but not decomposed. | `docs/schemas/api_schemas.md`, `stream_lite/schemas/api/*.schema.json` |
| Event schema names and required envelope fields were not materialized. | `docs/schemas/events.md`, `stream_lite/schemas/events/*.schema.json` |
| Logical table ownership and transaction boundaries were not centralized. | `docs/data/logical_model.md` |
| Environment variables were requirements-backed but not cataloged. | `.env.example`, `docs/operations/environment_variables.md` |
| Metrics were required but not cataloged with labels and owners. | `docs/operations/prometheus_metrics.md` |
| Fault, retry, and quarantine behavior needed implementation-facing tables. | `docs/operations/retry_policy.md`, `docs/operations/fault_tolerance.md`, `docs/operations/quarantine_policy.md` |
| Streamlit controls needed route-level mapping. | `docs/streamlit/control_matrix.md` |
| Verification evidence needed concrete file targets. | `docs/verification/verification_matrix.md`, `docs/verification/acceptance_test_plan.md`, `docs/verification/evidence_index.md` |

### Remaining Before Code Generation

- Create example request/response fixtures for each active API schema.
- Create example event fixtures for each active event schema.
- Convert logical data model into migration design.
- Add contract lint scripts to enforce `.env.example`, schemas, metrics, and verification matrix parity.
- Decide exact package/module layout for implementation; this is an implementation planning decision, not a product behavior decision.
