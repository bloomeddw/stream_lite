# Event Schema Contract Inventory

Redis Streams is the active v0.1 broker. All events shall be serialized as JSON with `schema_version`, `event_type`, `event_id`, `correlation_id`, `occurred_at`, and an event-specific payload. Producers write events through the PostgreSQL `event_outbox`; consumers record Redis Stream IDs in `event_offsets`. Event schema files live under `stream_lite/schemas/events/`; valid and invalid example payloads live under `stream_lite/schemas/examples/events/`. Duration fields in event payloads shall use numeric seconds and field names ending `_seconds`.

## Shared Event Envelope

| Field | Type | Required | Contract |
|---|---|---:|---|
| `schema_version` | string | yes | Semantic version for event schema. v0.1 starts at `1.0.0`. |
| `event_type` | string | yes | Lowercase dot-separated event type. |
| `event_id` | uuid | yes | Globally unique event ID generated before outbox insert. |
| `idempotency_key` | string | yes | Deterministic key for duplicate handling. |
| `correlation_id` | uuid | yes | API or watcher boundary correlation ID. |
| `occurred_at` | rfc3339_utc | yes | Time business event occurred. |
| `producer` | string | yes | Owner service name. |
| `job_id` | uuid/null | event-specific | Required for job-scoped events. |
| `watcher_id` | uuid/null | event-specific | Required for watcher and job-scoped events. |
| `attempt_number` | integer/null | event-specific | Required for stage attempt events. |
| `payload` | object | yes | Event-specific payload. |

## Active v0.1 Event Types

| Event type | Stream | Producer | Consumers | Trigger state | Schema file | Example | Requirements |
|---|---|---|---|---|---|---|---|
| `file.detected` | `stream_lite.lifecycle` | watcher | watcher, validator, API summary | `DETECTED` committed | `stream_lite/schemas/events/file_detected.schema.json` | `stream_lite/schemas/examples/events/file_detected.valid.json` | SL-FDI-004, SL-LIFE-002 |
| `file.stable` | `stream_lite.lifecycle` | watcher | validator, API summary | `STABILIZING` complete | `stream_lite/schemas/events/file_stable.schema.json` | `stream_lite/schemas/examples/events/file_stable.valid.json` | SL-FDI-005 |
| `job.registered` | `stream_lite.lifecycle` | watcher | validator | `REGISTERED` committed | `stream_lite/schemas/events/job_registered.schema.json` | `stream_lite/schemas/examples/events/job_registered.valid.json` | SL-LIFE-003 |
| `job.state_changed` | `stream_lite.lifecycle` | stage owner | API summary, dashboard | any committed state transition | `stream_lite/schemas/events/job_state_changed.schema.json` | `stream_lite/schemas/examples/events/job_state_changed.valid.json` | SL-EVT-001, SL-EVT-017 |
| `file.validated` | `stream_lite.lifecycle` | validator | processor | `VALIDATED` committed | `stream_lite/schemas/events/file_validated.schema.json` | `stream_lite/schemas/examples/events/file_validated.valid.json` | SL-VAL-010 |
| `file.quarantined` | `stream_lite.lifecycle` | validator | API summary, dashboard | `QUARANTINED` committed | `stream_lite/schemas/events/file_quarantined.schema.json` | `stream_lite/schemas/examples/events/file_quarantined.valid.json` | SL-VAL-016 |
| `processing.started` | `stream_lite.lifecycle` | processor | API summary | `PROCESSING` committed | `stream_lite/schemas/events/processing_started.schema.json` | `stream_lite/schemas/examples/events/processing_started.valid.json` | SL-PRO-011 |
| `processing.completed` | `stream_lite.lifecycle` | processor | delivery | `PROCESSED` committed | `stream_lite/schemas/events/processing_completed.schema.json` | `stream_lite/schemas/examples/events/processing_completed.valid.json` | SL-PRO-012 |
| `processing.failed` | `stream_lite.lifecycle` | processor | retry scheduler, API summary | `RETRY_PENDING` or `FAILED` committed | `stream_lite/schemas/events/processing_failed.schema.json` | `stream_lite/schemas/examples/events/processing_failed.valid.json` | SL-PRO-014 |
| `delivery.started` | `stream_lite.lifecycle` | delivery | API summary | `DELIVERING` committed | `stream_lite/schemas/events/delivery_started.schema.json` | `stream_lite/schemas/examples/events/delivery_started.valid.json` | SL-OUT-002 |
| `delivery.completed` | `stream_lite.lifecycle` | delivery | API summary | `DELIVERED` committed | `stream_lite/schemas/events/delivery_completed.schema.json` | `stream_lite/schemas/examples/events/delivery_completed.valid.json` | SL-OUT-010 |
| `delivery.failed` | `stream_lite.lifecycle` | delivery | retry scheduler, API summary | `RETRY_PENDING`, `FAILED`, or `COMPLETED_WITH_DELIVERY_ERRORS` committed | `stream_lite/schemas/events/delivery_failed.schema.json` | `stream_lite/schemas/examples/events/delivery_failed.valid.json` | SL-OUT-018 |
| `retry.scheduled` | `stream_lite.lifecycle` | retry scheduler | worker owning next stage | `RETRY_PENDING` schedule due or created | `stream_lite/schemas/events/retry_scheduled.schema.json` | `stream_lite/schemas/examples/events/retry_scheduled.valid.json` | SL-RET-006, SL-EVT-022 |
| `job.completed` | `stream_lite.lifecycle` | delivery | API summary, dashboard | `COMPLETED` committed | `stream_lite/schemas/events/job_completed.schema.json` | `stream_lite/schemas/examples/events/job_completed.valid.json` | SL-LIFE-008 |
| `job.failed` | `stream_lite.lifecycle` | retry scheduler or stage owner | API summary, dashboard | `FAILED` committed | `stream_lite/schemas/events/job_failed.schema.json` | `stream_lite/schemas/examples/events/job_failed.valid.json` | SL-RET-009, SL-EVT-023 |

## Compatibility Rules

- Adding optional fields is backward compatible.
- Removing or renaming required fields requires a major schema version and migration note.
- Consumers shall ignore unknown optional fields and reject events missing required envelope fields.
- Consumer idempotency shall use `idempotency_key` plus consumer group name.

## Event Fixture Rule

Each active event schema shall have at least one valid event fixture under `schemas/examples/events/`. Every active event schema shall also include one `*.invalid.json` fixture before implementation tests are generated; additional enum, timestamp, and payload-specific invalid fixtures may be added later.
