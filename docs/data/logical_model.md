# Logical Data Model

This document defines the v0.1 PostgreSQL logical model. It is not a migration file; implementation shall create migrations that preserve these ownership and field contracts.

## Table Inventory

| Table | Owner service | Primary key | Purpose | Required relationship | Requirements |
|---|---|---|---|---|---|
| `watchers` | API | `watcher_id` | Persist watcher identity, lifecycle state, route policy, and presentation-independent configuration. | Has many sources, destinations, commands, jobs. | SL-FWM-001, SL-API-002 |
| `watcher_sources` | API | `source_folder_id` | Persist configured source folders, original tag text, normalized tags, latest health. | Belongs to watcher. | SL-FWM-020 |
| `watcher_destinations` | API | `destination_folder_id` | Persist configured destination folders, original tag text, normalized tags, latest health. | Belongs to watcher. | SL-FWM-021 |
| `watcher_route_matches` | API | `route_match_id` | Persist computed source-to-destination route matches for preview and enabled watcher configs. | Belongs to watcher, source, and destination. | SL-FWM-026, SL-JOB-016 |
| `control_commands` | API | `command_id` | Track async command acceptance and completion. | Targets watcher or job. | SL-LIFE-001 |
| `files` | watcher | `file_id` | Persist immutable source file identity and deduplication key before job registration. | Belongs to watcher and source. | SL-FDI-015, SL-JOB-004 |
| `jobs` | watcher | `job_id` | Current job state and source identity. | Belongs to watcher and source. | SL-FDI-004, SL-JOB-001 |
| `job_state_history` | all stage owners | `history_id` | Append-only lifecycle transition log. | Belongs to job. | SL-LIFE-009 |
| `validation_attempts` | validator | `validation_attempt_id` | Validation outcome, reason codes, and policy version. | Belongs to job. | SL-VAL-001 |
| `processing_attempts` | processor | `processing_attempt_id` | Spark attempt metadata, staging artifact, summary locator. | Belongs to job. | SL-PRO-005 |
| `delivery_attempts` | delivery | `delivery_attempt_id` | Per-destination delivery status, output paths, checksums, manifest locator. | Belongs to job and destination. | SL-OUT-006 |
| `output_manifests` | delivery | `output_manifest_id` | Persist finalized output manifest locator, checksum, and destination outcome summary. | Belongs to job and delivery attempts. | SL-OUT-010, SL-DCT-011 |
| `retry_schedules` | retry scheduler | `retry_schedule_id` | Due retry attempts and backoff parameters. | Belongs to job and failed stage. | SL-RET-004 |
| `event_outbox` | stage owner transaction | `outbox_id` | Durable event publication queue. | References job when job-scoped. | SL-EVT-011 |
| `event_offsets` | event consumers | `event_offset_id` | Consumer group offsets for Redis Stream IDs. | Unique stream and group. | SL-EVT-006 |
| `idempotency_keys` | API + workers | `idempotency_key_id` | Deduplicate API commands and worker side effects. | Scoped by actor/resource/payload hash. | SL-API-007 |
| `stage_ownership_claims` | workers | `claim_id` | Worker lease and recovery for eligible stages. | References job, stage, attempt. | SL-LIFE-017 |
| `duplicate_suppression_observations` | watcher | `duplicate_observation_id` | Record duplicate file arrivals without creating new jobs. | Links observed duplicate to original job. | SL-LIFE-013 |
| `quarantine_records` | validator | `quarantine_record_id` | Durable quarantine copy result and operator reason. | Belongs to invalid job. | SL-VAL-016 |
| `operational_log_summaries` | all services | `log_summary_id` | Persist dashboard-queryable log summaries. | Optional job/watcher link. | SL-OBS-008 |
| `health_observations` | API + watcher | `health_observation_id` | Persist bounded dependency/folder health observations for dashboard summaries. | May reference watcher or folder. | SL-RUN-013, SL-FWM-018, SL-OBS-013 |

## Required Field Groups

| Field group | Tables | Fields |
|---|---|---|
| Audit | all tables | `created_at`, `updated_at` where mutable, `correlation_id` where request/event scoped. |
| Job source identity | `jobs`, `duplicate_suppression_observations` | `watcher_id`, `source_folder_id`, `source_display_path`, `source_size_bytes`, `source_sha256`, `detected_at`. |
| State transition | `jobs`, `job_state_history` | `previous_state`, `new_state`, `actor_service`, `reason_code`, `transitioned_at`. |
| Retry | `retry_schedules`, attempts | `attempt_number`, `max_attempts`, `next_attempt_at`, `backoff_ms`, `failure_class`, `last_error_code`. |
| Event outbox | `event_outbox` | `event_id`, `event_type`, `stream_name`, `payload_json`, `status`, `publish_attempts`, `next_publish_at`, `published_stream_id`. |
| Path safety | folder/job/delivery/quarantine tables | `display_path`, `container_path`, never host-only absolute path in operator-facing fields. |

## Ownership Rules

- The API owns watcher configuration and command records.
- The watcher owns job creation and duplicate suppression observations.
- The validator owns validation attempts and quarantine records.
- The processor owns processing attempts and staging output references.
- The delivery service owns delivery attempts and output manifest references.
- The retry scheduler owns retry schedule due-time updates.
- The outbox dispatcher owns only publication status fields on `event_outbox`.

## State Consistency Rules

- A job current state shall equal the latest `job_state_history.new_state` by transition time and sequence.
- A stage owner shall update attempt row, job row, state history row, and event outbox row in one transaction when a state transition emits an event.
- `event_outbox` records shall not be deleted during normal operation; cleanup requires a future retention requirement.
