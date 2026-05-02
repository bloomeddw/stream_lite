# Database Migration Plan

## Intent

This document decomposes the logical data model into migration-ready table contracts before persistence code or Alembic migrations are generated. It is a design artifact only; it does not create runtime code.

## Migration Conventions

| Rule | Contract |
|---|---|
| Migration tool | Alembic shall be used when implementation begins unless a later decision supersedes this plan. |
| Identifier type | Primary identifiers shall use PostgreSQL `uuid` columns with application-owned UUID generation before insert. Database UUID defaults shall not be used for MVP primary application identities; see `docs/design/DEC-009-uuid-generation-ownership.md`. |
| Timestamps | Audit timestamps shall use `timestamptz` and UTC semantics. |
| JSON fields | `jsonb` shall be used only for bounded payloads where schema evolution is required, and each JSONB field shall point to a JSON schema or documented contract. |
| Enum strategy | MVP migrations shall use check constraints for lifecycle states and statuses to simplify rollback in the demo profile. |
| Idempotency | Idempotency keys shall have unique constraints scoped to the command/event/consumer context that consumes them. |
| Rollback | Each migration shall include a downgrade path or a documented no-downgrade rationale in the migration header. |

## Planned Migration Order

| Order | Migration concern | Tables | Requirements |
|---:|---|---|---|
| 1 | Core watcher configuration | `watchers`, `watcher_sources`, `watcher_destinations`, `watcher_route_matches` | SL-FWM-020, SL-FWM-031, SL-SEC-001 |
| 2 | Job and file metadata | `files`, `jobs`, `job_state_history` | SL-FDI-015, SL-JOB-001, SL-LIFE-009 |
| 3 | Validation and quarantine | `validation_attempts`, `quarantine_records` | SL-VAL-010, SL-VAL-016 |
| 4 | Processing and output artifacts | `processing_attempts`, `output_manifests`, `delivery_attempts` | SL-PRO-016, SL-OUT-010, SL-OUT-018 |
| 5 | Retry, command, ownership, and idempotency tracking | `retry_schedules`, `control_commands`, `idempotency_keys`, `stage_ownership_claims` | SL-RET-006, SL-RET-012, SL-LIFE-015, SL-JOB-014 |
| 6 | Event outbox and offsets | `event_outbox`, `event_offsets` | SL-EVT-002, SL-EVT-011, SL-EVT-015 |
| 7 | Operational summaries and duplicate observations | `duplicate_suppression_observations`, `operational_log_summaries`, `health_observations` | SL-LIFE-013, SL-OBS-008, SL-FWM-018, SL-OBS-013 |

## Table Contracts

### `watchers`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `watcher_id` | `uuid` | primary key | Stable watcher identity. |
| `name` | `text` | not null, unique | Operator-visible name. |
| `lifecycle_state` | `text` | not null, check in watcher states | `CREATED`, `ACTIVE`, `PAUSED`, `STOPPING`, `STOPPED`, `ERROR`. |
| `operational_status` | `text` | not null, check in `green/yellow/red` | Dashboard status. |
| `route_policy` | `text` | not null, check `tag_match_all_destinations` | MVP routing policy. |
| `enabled` | `boolean` | not null default false | Whether watcher may run. |
| `created_at`, `updated_at` | `timestamptz` | not null | UTC timestamps. |

Indexes: unique `name`; btree `(lifecycle_state, operational_status)` for dashboard filters.

### `watcher_sources` and `watcher_destinations`

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `folder_id` | `uuid` | primary key | Source/destination identity. |
| `watcher_id` | `uuid` | foreign key to `watchers` | Owning watcher. |
| `folder_role` | `text` | check `source/destination` | Role-specific table may omit this when split. |
| `display_path` | `text` | not null | Sanitized path only. |
| `normalized_path` | `text` | not null | Container path after allowlist normalization. |
| `route_tags` | `text[]` | not null | Normalized tags. |
| `route_tags_text` | `text` | not null | Original operator entry. |
| `health_status` | `text` | not null | `green/yellow/red`. |
| `reason_code` | `text` | nullable | Operator-safe reason. |

Indexes: `(watcher_id)`, GIN on `route_tags`, unique `(watcher_id, normalized_path, folder_role)`.

### `files`, `jobs`, and `job_state_history`

| Table | Required columns | Key constraints and indexes |
|---|---|---|
| `files` | `file_id`, `watcher_id`, `source_folder_id`, `source_display_path`, `size_bytes`, `sha256`, `first_seen_at`, `deduplication_key` | Unique `deduplication_key`; index `(watcher_id, source_folder_id)`. |
| `jobs` | `job_id`, `file_id`, `watcher_id`, `source_folder_id`, `state`, `attempt_number`, `correlation_id`, `created_at`, `updated_at`, `latest_error_code` | FK to `files`; index `(state, updated_at)` for stage ownership; unique `job_id`. |
| `job_state_history` | `transition_id`, `job_id`, `from_state`, `to_state`, `actor_service`, `reason_code`, `event_id`, `occurred_at`, `correlation_id` | FK to `jobs`; index `(job_id, occurred_at)`; unique `event_id`. |

### `validation_attempts` and `quarantine_records`

`validation_attempts` shall persist rule results, duration seconds, status, and reason codes. `quarantine_records` shall persist the fields required by `SL-VAL-016` before `file.quarantined` publication.

Indexes: `(job_id, attempt_number)` unique for validation attempts; `(job_id)` and `(created_at)` for quarantine records.

### `processing_attempts`, `output_manifests`, and `delivery_attempts`

`processing_attempts` shall record engine, version, input/output locators, row counts when available, duration seconds, and status. `output_manifests` shall record checksum and produced output locators. `delivery_attempts` shall be one row per matched destination and preserve per-destination outcome.

Indexes: `(job_id, attempt_number)`; `(job_id, destination_folder_id, attempt_number)`; `(status, updated_at)` for retry reconciliation.

### `retry_schedules`, `control_commands`, and `idempotency_keys`

`retry_schedules` shall store due time, backoff seconds, attempt number, max attempts, stage, and failure class. `control_commands` shall support accepted/running/succeeded/failed/expired command states for dashboard polling. `idempotency_keys` shall scope keys by route or command type and target ID.

Indexes: `(due_at, status)` for retry scheduler; unique `(scope, idempotency_key)`.

### `event_outbox` and `event_offsets`

`event_outbox` shall persist the full event envelope, payload JSONB, stream name, publication status, attempt count, next publish time, and error code. `event_offsets` shall persist consumer group, stream name, Redis stream ID, and last processed event ID.

Indexes: `(publish_status, next_publish_at)`, `(event_type, occurred_at)`, unique `event_id`, unique `(consumer_group, stream_name)`.

### `operational_log_summaries` and `health_observations`

These tables shall store dashboard-queryable operational summaries without exposing raw host paths or secrets. Raw logs may remain stdout-only in MVP; summaries shall contain bounded fields suitable for `GET /logs` and dashboard cards.

## Verification

| Verification ID | Method | Evidence |
|---|---|---|
| V-DATA-MIGRATION-001 | Design review | This migration plan and logical model review notes. |
| V-DATA-MIGRATION-002 | Future migration test | Alembic upgrade/downgrade logs when migrations are generated. |
| V-DATA-MIGRATION-003 | Contract lint | Script output confirming required migration design sections exist before persistence code is added. |

## Closed Decisions

- UUID generation ownership is application-owned for v0.1; see `docs/design/DEC-009-uuid-generation-ownership.md`.
- Alembic skeleton remains deferred until implementation planning is approved.
- Concrete migration files remain deferred until schema contracts and L3 persistence surfaces are stable.

## Repository Traceability for Migration Tables

Future persistence code shall not create a repository function for a table unless the corresponding L3 requirement below is implemented and verified.

| Table | Repository requirement | UUID ownership | Notes |
|---|---|---|---|
| `watchers` | SL-JOB-031 | application | Root watcher identity. |
| `watcher_sources` | SL-JOB-032 | application | Source folder identity. |
| `watcher_destinations` | SL-JOB-033 | application | Destination folder identity. |
| `watcher_route_matches` | SL-JOB-034 | application | Route preview/match identity. |
| `files` | SL-JOB-035 | application | Immutable file identity before job creation. |
| `jobs` | SL-JOB-036 | application | Job identity generated at registration boundary. |
| `job_state_history` | SL-JOB-037 | application | Transition identity generated by state transition surface. |
| `validation_attempts` | SL-JOB-038 | application | Validation attempt identity. |
| `quarantine_records` | SL-JOB-039 | application | Quarantine record identity. |
| `processing_attempts` | SL-JOB-040 | application | Processing attempt identity. |
| `output_manifests` | SL-JOB-041 | application | Output manifest identity. |
| `delivery_attempts` | SL-JOB-042 | application | Delivery attempt identity. |
| `retry_schedules` | SL-JOB-043 | application | Retry schedule identity. |
| `control_commands` | SL-JOB-044 | application | Command identity generated at API boundary. |
| `idempotency_keys` | SL-JOB-045 | application | Idempotency record identity; key value remains operator/request supplied or derived. |
| `stage_ownership_claims` | SL-JOB-046 | application | Claim identity generated before worker side effects. |
| `duplicate_suppression_observations` | SL-JOB-047 | application | Observation identity generated by watcher duplicate check. |
| `event_outbox` | SL-JOB-048 | application | `outbox_id` and `event_id` generated in stage-owner transaction. |
| `event_offsets` | SL-JOB-049 | application | Offset identity generated by consumer. |
| `operational_log_summaries` | SL-JOB-050 | application | Summary identity generated by log-summary writer. |
| `health_observations` | SL-JOB-051 | application | Health observation identity generated by health checker. |

### `stage_ownership_claims` and `duplicate_suppression_observations`

`stage_ownership_claims` shall store worker leases for validation, processing, delivery, retry, and outbox stages with stage, owner service, attempt number, lease expiration, claim status, and recovery metadata. `duplicate_suppression_observations` shall store duplicate file arrivals linked to the existing job and shall not create a new job lifecycle.

Indexes: `(stage, claim_status, lease_expires_at)` for recovery; `(existing_job_id, observed_at)` for duplicate observation review; unique claim guard by `(job_id, stage, attempt_number)` where claim is active.
