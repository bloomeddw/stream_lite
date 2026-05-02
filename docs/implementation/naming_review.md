# Final Naming Review Before Codex Implementation

## Purpose

This review freezes first-pass names for modules, route handlers, repositories, workers, services, and artifact writers before Codex starts generating runtime code. The goal is to reduce churn and prevent implementation agents from inventing parallel names for the same requirement surface.

## Status

| Area | Status | Notes |
|---|---|---|
| Module layout | Accepted for implementation start | See `docs/implementation/CODEX_TASK_GUIDE.md`. |
| Repository names | Accepted for implementation start | Names align with migration tables and L3 persistence rows in `REQ-006`. |
| API route-handler names | Accepted for implementation start | Names align with `docs/api/endpoints.md` and `REQ-010` L3 rows. |
| Event producer/dispatcher names | Accepted for implementation start | Names align with event outbox and Redis Streams contracts. |
| Worker/service names | Accepted for implementation start | Names align with watcher, validation, processing, delivery, and retry requirements. |
| Metric units | Accepted | Durations use seconds. Do not use `_duration_ms`. |
| UUID ownership | Accepted | Application-owned UUID generation; see `DEC-009`. |

## Repository Name Map

| Durable table or concern | Repository class/module | Core methods Codex should start with | Requirements |
|---|---|---|---|
| `watchers` | `WatcherRepository` / `repositories/watchers.py` | `create_watcher`, `get_watcher`, `list_watchers`, `update_watcher_state` | SL-JOB-031, SL-FWM-020 |
| `watcher_sources` | `WatcherRepository` | `replace_sources`, `list_sources` | SL-JOB-032, SL-FWM-020 |
| `watcher_destinations` | `WatcherRepository` | `replace_destinations`, `list_destinations` | SL-JOB-033, SL-FWM-020 |
| `watcher_route_matches` | `WatcherRepository` | `save_route_preview`, `list_route_matches` | SL-JOB-034, SL-FWM-021 |
| `files` | `FileRepository` / `repositories/files.py` | `create_file_record`, `get_by_deduplication_key` | SL-JOB-035, SL-FDI-015 |
| `jobs` | `JobRepository` / `repositories/jobs.py` | `create_job`, `get_job`, `list_jobs`, `update_state` | SL-JOB-036, SL-JOB-001 |
| `job_state_history` | `JobRepository` | `append_state_transition`, `list_state_history` | SL-JOB-037, SL-LIFE-009 |
| `validation_attempts` | `ValidationRepository` / `repositories/validation.py` | `create_validation_attempt`, `get_latest_attempt` | SL-JOB-038, SL-VAL-010 |
| `quarantine_records` | `ValidationRepository` | `create_quarantine_record`, `list_quarantine_records` | SL-JOB-039, SL-VAL-016 |
| `processing_attempts` | `ProcessingRepository` / `repositories/processing.py` | `create_processing_attempt`, `complete_processing_attempt`, `fail_processing_attempt` | SL-JOB-040, SL-PRO-016 |
| `output_manifests` | `DeliveryRepository` / `repositories/delivery.py` | `create_output_manifest`, `get_output_manifest` | SL-JOB-041, SL-OUT-010 |
| `delivery_attempts` | `DeliveryRepository` | `create_delivery_attempt`, `complete_delivery_attempt`, `fail_delivery_attempt` | SL-JOB-042, SL-OUT-018 |
| `retry_schedules` | `RetryRepository` / `repositories/retry.py` | `schedule_retry`, `claim_due_retries`, `mark_retry_exhausted` | SL-JOB-043, SL-RET-006 |
| `control_commands` | `CommandRepository` / `repositories/commands.py` | `create_command`, `get_command`, `update_command_status` | SL-JOB-044, SL-RET-012 |
| `idempotency_keys` | `CommandRepository` | `reserve_idempotency_key`, `get_existing_result` | SL-JOB-045, SL-LIFE-015 |
| `stage_ownership_claims` | `StageClaimRepository` / `repositories/stage_claims.py` | `claim_stage`, `renew_claim`, `release_claim`, `recover_expired_claims` | SL-JOB-046, SL-LIFE-016 |
| `duplicate_suppression_observations` | `FileRepository` | `record_duplicate_observation`, `list_duplicate_observations` | SL-JOB-047, SL-LIFE-013 |
| `event_outbox` | `EventOutboxRepository` / `repositories/events.py` | `enqueue_event`, `claim_due_events`, `mark_published`, `mark_dead_lettered` | SL-JOB-048, SL-EVT-011 |
| `event_offsets` | `EventOffsetRepository` / `repositories/events.py` | `get_offset`, `upsert_offset` | SL-JOB-049, SL-EVT-011 |
| `operational_log_summaries` | `OperationalLogRepository` / `repositories/logs.py` | `write_summary`, `list_summaries` | SL-JOB-050, SL-OBS-008 |
| `health_observations` | `HealthRepository` / `repositories/health.py` | `write_observation`, `get_latest_observations` | SL-JOB-051, SL-OBS-013 |

## API Route Handler Name Map

| Route group | Module | Handler names | Requirements |
|---|---|---|---|
| `/health` | `api/routes/health.py` | `get_health`, `get_dependency_health` | SL-API-031, SL-API-041 |
| `/metrics` | `api/routes/metrics.py` | `get_metrics_text`, `get_metrics_summary` | SL-API-033, SL-API-043 |
| `/watchers` | `api/routes/watchers.py` | `list_watchers`, `create_watcher`, `get_watcher`, `patch_watcher`, `post_watcher_lifecycle` | SL-API-034, SL-API-035, SL-API-044, SL-API-045 |
| `/jobs` | `api/routes/jobs.py` | `list_jobs`, `get_job`, `get_job_history`, `post_job_retry` | SL-API-036, SL-API-037, SL-API-046, SL-API-047 |
| `/events` | `api/routes/events.py` | `list_events` | SL-API-032, SL-API-042 |
| `/files` | `api/routes/files.py` | `browse_folders`, `validate_path`, `preview_routes` | SL-API-038, SL-API-048 |
| `/config` | `api/routes/config.py` | `get_dashboard_presentation` | SL-API-039, SL-API-049 |
| `/operations` | `api/routes/operations.py` | `list_operational_logs`, `get_command_status` | SL-API-040, SL-API-050 |

## Worker and Service Name Map

| Capability | Module | Surface names | Requirements |
|---|---|---|---|
| Watcher lifecycle | `watcher/service.py` | `WatcherService.start`, `stop`, `poll_once` | SL-FWM-022, SL-FWM-031 |
| Route matching | `watcher/routing.py` | `RouteMatcher.preview_routes`, `match_destinations` | SL-FWM-021 |
| File stability | `watcher/stability.py` | `FileStabilityDetector.is_stable` | SL-FDI-022 |
| Duplicate suppression | `watcher/deduplication.py` | `DuplicateSuppressionService.check_or_record` | SL-FDI-025, SL-LIFE-013 |
| Validation | `validation/validator.py` | `FileValidator.validate_file` | SL-VAL-001 through SL-VAL-010 |
| Quarantine | `validation/quarantine.py` | `QuarantineService.quarantine_file` | SL-VAL-016 |
| Processing | `processing/engine.py` | `ProcessingWorker.claim_and_process` | SL-PRO-016 |
| Delivery | `delivery/service.py` | `DeliveryWorker.claim_and_deliver` | SL-OUT-018 |
| Retry | `retry/scheduler.py` | `RetryScheduler.schedule_due_retries` | SL-RET-006 |
| Manual retry | `retry/scheduler.py` | `ManualRetryService.accept_command` | SL-RET-012 |
| Event dispatch | `events/dispatcher.py` | `EventDispatcher.publish_due_events` | SL-EVT-011 |
| Metrics | `observability/metrics.py` | `record_api_latency_seconds`, `record_stage_duration_seconds` | SL-OBS-005, SL-OBS-006 |
| Logs | `observability/logging.py` | `build_structured_log`, `redact_sensitive_fields` | SL-OBS-001, SL-SEC-015 |

## Naming Guardrails

1. Use singular repository class names even when backing tables are plural.
2. Use route handler names with HTTP verb intent only when useful; avoid framework-specific names in requirements.
3. Use `*_seconds` for duration fields and metrics.
4. Use `*_at` for timestamps with UTC/RFC3339 semantics.
5. Use `*_id` for UUID identity fields.
6. Use `locator` for safe artifact/output references and `display_path` for operator-safe paths.
7. Avoid `path` in public API responses unless the value is explicitly safe and documented.
