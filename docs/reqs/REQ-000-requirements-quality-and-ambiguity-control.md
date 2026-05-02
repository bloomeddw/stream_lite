# REQ-000: Requirements Quality and Ambiguity Control

## Capability Intent

The requirements baseline shall be precise enough for implementation by a human developer or coding agent without relying on unstated assumptions. Requirements shall make scope, interfaces, state changes, failure behavior, verification methods, and evidence artifacts explicit before code is written.

## Requirement Decomposition Levels

Stream Lite requirements use three decomposition levels. Existing capability files are treated as L1 until decomposed. New or materially modified requirements shall identify the lowest applicable level in nearby section text or table context.

| Level | Purpose | Required contents | Example artifacts |
|---|---|---|---|
| L1 capability requirement | Describes the externally visible capability, operator outcome, or system invariant. | Intent, scope boundary, priority, verification method, acceptance criteria, owner requirement file. | `REQ-010` FastAPI control plane; `REQ-005` event streaming. |
| L2 contract requirement | Decomposes an L1 capability into explicit interface, schema, state, event, retry, metric, log, or environment contracts. | Contract fields, allowed values, status codes, state transitions, producer/consumer, timeout, log event, metric, evidence artifact. | Endpoint matrix row, event schema row, env var row, retry policy row. |
| L3 implementation trace requirement | Decomposes an L2 contract into named implementation surfaces that must exist and be tested. | Module/function/route handler name, inputs, outputs, side effects, failure response, idempotency behavior, test target, evidence artifact. | `list_events` route handler, `schedule_retry` service function, schema validation test. |

L1 requirements may remain broad only when each implementation-facing behavior is decomposed into L2 or L3 before code work begins. L2 and L3 requirements shall remain in the owning capability file rather than a separate meta-requirement file.

## Ambiguity Control Rules

| Rule ID | Rule | Verification |
|---|---|---|
| SL-REQ-QUAL-001 | Every requirement using `shall` shall include a stable requirement ID, priority, and verification ID. | V-SL-REQ-QUAL-001 |
| SL-REQ-QUAL-002 | A requirement shall not use subjective qualifiers such as `easy`, `simple`, `reasonable`, `appropriate`, `robust`, `good`, or `safe` unless the same row or an adjacent contract table defines measurable behavior. | V-SL-REQ-QUAL-002 |
| SL-REQ-QUAL-003 | A requirement that uses `configurable` shall name the configuration surface: environment variable, API field, dashboard field, config file, or database-backed setting. | V-SL-REQ-QUAL-003 |
| SL-REQ-QUAL-004 | A requirement that uses `when supported`, `where possible`, or `or equivalent` shall define the fallback behavior, status code, log event, metric, and operator-visible message. | V-SL-REQ-QUAL-004 |
| SL-REQ-QUAL-005 | A requirement that introduces an API endpoint shall specify method, route, request schema name, response schema name, status codes, error codes, idempotency behavior, timeout target, log event, metric, and related requirement IDs before implementation. | V-SL-REQ-QUAL-005 |
| SL-REQ-QUAL-006 | A requirement that introduces an event shall specify event type, topic or stream, producer, consumer, schema version, required fields, idempotency key, ordering expectation, retry/dead-letter behavior, and related requirement IDs before implementation. | V-SL-REQ-QUAL-006 |
| SL-REQ-QUAL-007 | A requirement that introduces a state transition shall specify the source state, target state, permitted actor, preconditions, persistence order, event/log emission, retry handling, and invalid-transition response. | V-SL-REQ-QUAL-007 |
| SL-REQ-QUAL-008 | A requirement that introduces an environment variable shall be captured in `.env.example` and `docs/operations/environment_variables.md` with purpose, default, allowed values, sensitivity, owner, missing behavior, invalid behavior, and related requirement IDs. | V-SL-REQ-QUAL-008 |
| SL-REQ-QUAL-009 | A requirement that introduces a metric shall be captured in `docs/operations/prometheus_metrics.md` with metric name, type, labels, owner, trigger, threshold where applicable, Streamlit use, and related requirement IDs. | V-SL-REQ-QUAL-009 |
| SL-REQ-QUAL-010 | A requirement shall distinguish MVP/demo behavior from future enhancement behavior in the same section where the feature is introduced. | V-SL-REQ-QUAL-010 |

## Verification Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-REQ-001 | The repository shall include a requirements lint pass that scans requirement Markdown for missing IDs, missing verification IDs, duplicate IDs, and prohibited ambiguous terms not covered by a local definition. | Must | V-SL-REQ-001 |
| SL-REQ-002 | The verification matrix shall include one row for each `Must` requirement and shall report `planned`, `implemented`, `passed`, `failed`, or `deferred` status. | Must | V-SL-REQ-002 |
| SL-REQ-003 | Every requirements-changing patch shall include a worklog that lists changed files, affected requirement IDs, decisions applied, tests or checks performed, assumptions, gaps, and rollback notes. | Must | V-SL-REQ-003 |
| SL-REQ-004 | Implementation shall not begin for any route, event, environment variable, metric, retry rule, state transition, Streamlit control, or Sphinx-generated page until the relevant requirement and verification entry exist. | Must | V-SL-REQ-004 |
| SL-REQ-005 | Every externally referenced requirement ID shall resolve to one active requirement row in an owning `REQ-###.md` file, excluding verification IDs prefixed with `V-SL-`. | Must | V-SL-REQ-005 |
| SL-REQ-006 | When an unresolved externally referenced requirement ID is found, the requirement owner shall either add the missing requirement to the best-fit owning capability file or replace the reference with an existing adjacent requirement ID and document the rationale in the worklog. | Must | V-SL-REQ-006 |
| SL-REQ-007 | Requirement decomposition shall use L1, L2, and L3 levels: L1 for capability intent, L2 for contracts, and L3 for implementation surfaces and function-level traceability. | Must | V-SL-REQ-007 |
| SL-REQ-008 | L3 implementation trace requirements shall not introduce hidden behavior; each L3 row shall point back to at least one L1 or L2 requirement and one verification method. | Must | V-SL-REQ-008 |

## Acceptance Criteria

This requirement is accepted when a requirements lint report shows no duplicate requirement IDs, every `Must` requirement has a verification ID, all newly introduced implementation surfaces have matching contract documentation, and every patch includes a worklog under `stream_lite/docs/worklogs/`.


## Contract Artifact Readiness Requirements

These L2 requirements replace the former standalone decomposition capability file. They belong in `REQ-000` because they govern requirements quality, traceability, and implementation readiness across all capability files.

| ID | Level | Requirement | Priority | Verification |
|---|---|---|---:|---|
| SL-DECOMP-001 | L2 | The repository shall include an API contract document that lists every active v0.1 route, method, schema name, status code, idempotency rule, timeout target, log event, metric, owner service, and owning requirement IDs. | Must | V-SL-DECOMP-001 |
| SL-DECOMP-002 | L2 | The repository shall include machine-readable API schema stubs for active mutation and detail/list response payloads before API implementation begins. | Must | V-SL-DECOMP-002 |
| SL-DECOMP-003 | L2 | The repository shall include event schema files for every active v0.1 lifecycle event emitted through Redis Streams before event producer or consumer implementation begins. | Must | V-SL-DECOMP-003 |
| SL-DECOMP-004 | L2 | The repository shall include a logical data model that maps each table to owner service, primary key, required fields, lifecycle purpose, and related requirement IDs. | Must | V-SL-DECOMP-004 |
| SL-DECOMP-005 | L2 | The repository shall include an environment variable catalog and `.env.example` that cover every v0.1 variable referenced by requirements or contract docs. | Must | V-SL-DECOMP-005 |
| SL-DECOMP-006 | L2 | The repository shall include a Prometheus metrics catalog that covers API latency, watcher status, folder health, job state counts, stage durations, event publication, queue lag, retry outcomes, delivery outcomes, dashboard actions, and error counts. | Must | V-SL-DECOMP-006 |
| SL-DECOMP-007 | L2 | The repository shall include retry, fault tolerance, and quarantine policy documents that define detection point, retryability, backoff, terminal state, operator message, log event, metric, and recovery path for each active v0.1 failure class. | Must | V-SL-DECOMP-007 |
| SL-DECOMP-008 | L2 | The repository shall include a Streamlit control matrix that maps every operator control to API route, request schema, allowed states, validation rule, success/failure response, log event, metric, and requirement IDs. | Must | V-SL-DECOMP-008 |
| SL-DECOMP-009 | L2 | The repository shall include a verification matrix that maps every active requirement family and contract artifact to at least one verification method and evidence artifact. | Must | V-SL-DECOMP-009 |
| SL-DECOMP-010 | L2 | Implementation planning shall not assign code tasks for a component until that component has API, event, data, environment, metrics, failure, and verification contracts for the behavior being implemented. | Must | V-SL-DECOMP-010 |
