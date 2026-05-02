# REQ-005: Event Streaming Requirements

## Capability Intent

The system shall coordinate services through durable processing events so that file detection, validation, processing, delivery, retry, and dashboard updates are not tightly coupled through synchronous calls alone.

## Broker Options

The v0.1 MVP shall support one active broker profile:

- `redis_streams`: lightweight local development and proof-of-concept profile.

Future-compatible but inactive scope:

- `redpanda`: Kafka-compatible event streaming profile for stronger production resemblance. A v0.1 service that receives `STREAM_LITE_BROKER_PROFILE=redpanda` shall fail startup with `CONFIG_UNSUPPORTED_DEFERRED_PROFILE` rather than partially enabling an unverified broker path.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-EVT-001 | The system shall publish a machine-readable event for every job state transition. | Must | V-SL-EVT-001 |
| SL-EVT-002 | Each event shall include `event_id`, `event_type`, `job_id`, `watcher_id`, `occurred_at`, `producer`, `schema_version`, and `payload`. | Must | V-SL-EVT-002 |
| SL-EVT-003 | Event IDs shall be UUIDv7 or UUIDv4 values generated once per persisted event record and unique within a local deployment. | Must | V-SL-EVT-003 |
| SL-EVT-004 | Event payloads shall be JSON-serializable. | Must | V-SL-EVT-004 |
| SL-EVT-005 | Events shall be appended only after the related PostgreSQL state update commits, unless the event is explicitly marked as pre-commit telemetry. | Must | V-SL-EVT-005 |
| SL-EVT-006 | Consumers shall record Redis Stream IDs for every consumed v0.1 event; future Kafka-compatible topic/partition/offset recording shall not be implemented until Redpanda is activated by a later decision. | Must | V-SL-EVT-006 |
| SL-EVT-007 | Consumers shall tolerate at-least-once delivery by using idempotency key `<event_type>:<job_id>:<stage_attempt>:<destination_folder_id_or_none>` and shall persist processed idempotency keys before acknowledging the broker message. | Must | V-SL-EVT-007 |
| SL-EVT-008 | The system shall retain events for at least 24 hours in local demo mode or 10,000 events, whichever is larger; startup shall log the active retention setting. | Must | V-SL-EVT-008 |
| SL-EVT-009 | The dashboard shall not be the only consumer of operational state; it shall read from API and persisted metadata. | Must | V-SL-EVT-009 |
| SL-EVT-010 | The event schema shall be versioned. | Must | V-SL-EVT-010 |
| SL-EVT-011 | Every state-changing event shall be written to a PostgreSQL `event_outbox` record in the same transaction as the state or attempt record that caused it. | Must | V-SL-EVT-011 |
| SL-EVT-012 | The event dispatcher shall publish pending `event_outbox` records to Redis Streams and mark each outbox record as `published` only after the broker append succeeds. | Must | V-SL-EVT-012 |
| SL-EVT-013 | If broker publication fails, the outbox record shall remain `pending` or `publish_failed`, the dispatcher shall retry using the retry policy, and the related job state shall remain durable in PostgreSQL. | Must | V-SL-EVT-013 |
| SL-EVT-014 | Direct broker publication from a service shall be allowed only for explicitly documented pre-commit telemetry events; all job lifecycle events in v0.1 shall use the outbox path. | Must | V-SL-EVT-014 |
| SL-EVT-015 | The API shall expose `GET /events` to list persisted lifecycle events from the metadata store using documented pagination and filters; the endpoint shall not read Redis Streams directly as the source of truth. | Must | V-SL-EVT-015 |

## Event Type Decomposition Requirements

These L2 requirements decompose the L1 event-streaming capability into event-type contracts referenced by `docs/schemas/events.md`.

| ID | Level | Requirement | Priority | Verification |
|---|---|---|---:|---|
| SL-EVT-016 | L2 | The event schema inventory shall list each active v0.1 event type with stream name, producer, consumer group or reader, trigger state, schema file, and owning requirement IDs. | Must | V-SL-EVT-016 |
| SL-EVT-017 | L2 | The `job.state_changed` event shall be emitted for every committed job state transition and shall include previous state, new state, transition reason, stage owner, `job_id`, `watcher_id`, `correlation_id`, and schema version. | Must | V-SL-EVT-017 |
| SL-EVT-018 | L2 | The `file.detected`, `file.stable`, and `job.registered` events shall preserve detection order for the same source path and shall reference the same `job_id` once a job is allocated. | Must | V-SL-EVT-018 |
| SL-EVT-019 | L2 | Validation events shall distinguish successful validation from quarantine by using `file.validated` for accepted files and `file.quarantined` for files moved to quarantine with validation error code and quarantine record path. | Must | V-SL-EVT-019 |
| SL-EVT-020 | L2 | Processing events shall distinguish processing start, processing completion, and processing failure with attempt number, processing engine, input artifact reference, and output or error summary. | Must | V-SL-EVT-020 |
| SL-EVT-021 | L2 | Delivery events shall identify destination folder, delivery attempt, delivery outcome, output manifest reference, and destination-specific failure code when delivery fails. | Must | V-SL-EVT-021 |
| SL-EVT-022 | L2 | The `retry.scheduled` event shall be emitted when a retryable stage failure is committed to `RETRY_PENDING` and shall include next stage, attempt number, due time, backoff seconds, max attempts, and retry reason. | Must | V-SL-EVT-022 |
| SL-EVT-023 | L2 | The `job.failed` event shall be emitted when a job reaches final `FAILED` state after non-retryable failure or exhausted retries and shall include final failure class, exhausted stage, last error code, and operator-safe message. | Must | V-SL-EVT-023 |

## Required Event Types

- `file.detected`
- `file.stable`
- `job.registered`
- `job.state_changed`
- `file.validated`
- `file.quarantined`
- `processing.started`
- `processing.completed`
- `processing.failed`
- `delivery.started`
- `delivery.completed`
- `delivery.failed`
- `retry.scheduled`
- `job.completed`
- `job.failed`

## Event Ordering and Dead-Letter Contract

| Area | Requirement |
|---|---|
| Ordering scope | Events for the same `job_id` shall be emitted in the same order as committed job state history records. Cross-job ordering is not guaranteed in MVP. |
| Event topic/stream names | v0.1 MVP lifecycle events shall publish to `stream_lite.lifecycle`; dead-letter records shall publish to `stream_lite.dead_letter`. The older split streams `stream_lite.jobs`, `stream_lite.files`, `stream_lite.delivery`, and `stream_lite.commands` are deferred future scope unless a later accepted decision activates domain-specific stream partitioning and updates schemas, examples, API contracts, consumers, and tests together. |
| Acknowledgement | A consumer shall acknowledge a message only after the database side effect and processed idempotency record commit. |
| Consumer failure | A consumer failure before acknowledgement shall allow broker redelivery and shall not create duplicate jobs, state history rows, or finalized outputs. |
| Dead letter | After 3 failed consumer handling attempts for the same event, the event shall be copied to `stream_lite.dead_letter` with `original_event_id`, `consumer`, `failure_code`, `attempt_count`, and `last_error_message`. |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-EVT-NFR-001 | Event publish latency p95 after committed state transition | <= 500 ms |
| SL-EVT-NFR-002 | Event schema validation coverage | 100% of required event types |
| SL-EVT-NFR-003 | Consumer duplicate-event safety | 100% for duplicate fixture events |
| SL-EVT-NFR-004 | Event retention in local demo | >= 24 hours |
| SL-EVT-NFR-005 | Event loss under controlled service restart fixture | 0 committed state transitions without corresponding published outbox event |

## Acceptance Criteria

The requirement is accepted when a complete ingestion run writes outbox records, emits ordered schema-valid events for each state transition, recovers unpublished outbox records after broker restart, and downstream consumers can safely reprocess duplicate events without creating duplicate jobs or duplicate outputs.

## Applied Decision Records

| Decision | Requirement impact |
|---|---|
| DEC-003 broker profile | Active v0.1 event contract targets Redis Streams only. |
| DEC-010 event stream naming | Active v0.1 lifecycle events use `stream_lite.lifecycle`; `stream_lite.dead_letter` is reserved for dead-letter records; domain-specific split streams are deferred future scope. |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-EVT-024 | L3 | SL-EVT-002, SL-EVT-011 | `stream_lite.events.outbox.enqueue_event` | The outbox enqueue surface shall validate event schema, assign event ID and idempotency key, persist the event in PostgreSQL, and return the persisted event ID without publishing directly to Redis. | V-SL-EVT-024 |
| SL-EVT-025 | L3 | SL-EVT-011 | `stream_lite.events.dispatcher.publish_pending_events` | The dispatcher surface shall poll pending outbox rows, publish to Redis Streams, update publication status, increment attempt count on failure, and emit bounded logs and metrics. | V-SL-EVT-025 |
| SL-EVT-026 | L3 | SL-EVT-013, SL-EVT-015 | `stream_lite.events.repository.list_events` | The event listing surface shall page and filter event outbox records for `GET /events` without exposing raw payload fields not listed in the API event list schema. | V-SL-EVT-026 |
