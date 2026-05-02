# REQ-012: Operational Logging and Observability Requirements

## Capability Intent

The system shall provide enough logs, metrics, and audit trails for an operator or reviewer to understand what happened during an ingestion run, why a file failed, how long each stage took, whether the system is idle or active, how route tags were matched, which destinations received each output, and what evidence proves the system behaved correctly.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-OBS-001 | Each service shall emit JSON structured logs to stdout with required fields `timestamp`, `level`, `service`, `component`, `event`, `correlation_id`, `message`, and `duration_ms` when applicable. | Must | V-SL-OBS-001 |
| SL-OBS-002 | Logs related to a job shall include `job_id`; non-job logs shall set `job_id` to `null`. | Must | V-SL-OBS-002 |
| SL-OBS-003 | Logs related to a watcher shall include `watcher_id`; non-watcher logs shall set `watcher_id` to `null`. | Must | V-SL-OBS-003 |
| SL-OBS-004 | Every job state transition shall emit a structured log record. | Must | V-SL-OBS-004 |
| SL-OBS-005 | Every validation failure shall emit a structured log with reason code. | Must | V-SL-OBS-005 |
| SL-OBS-006 | Every processing attempt shall emit start and end logs. | Must | V-SL-OBS-006 |
| SL-OBS-007 | Every delivery attempt shall emit start and end logs. | Must | V-SL-OBS-007 |
| SL-OBS-008 | The API shall expose operational log summaries to the dashboard through `GET /logs`, backed by persisted log/event summary records rather than direct container log scraping in MVP. | Must | V-SL-OBS-008 |
| SL-OBS-009 | The system shall expose summary metrics for total jobs, active jobs, completed jobs, failed jobs, quarantined jobs, retries pending, and average stage duration. | Must | V-SL-OBS-009 |
| SL-OBS-010 | The system shall preserve error stack traces in service logs for unexpected exceptions while returning sanitized API errors that include `error_code`, operator-safe `message`, and `correlation_id` but exclude secrets and host-only paths. | Must | V-SL-OBS-010 |
| SL-OBS-011 | The system shall record processing and delivery durations as numeric metric fields. | Must | V-SL-OBS-011 |
| SL-OBS-012 | The system shall provide `GET /metrics/summary` and a generated `summary.md` evidence artifact for demo review after acceptance tests run. | Must | V-SL-OBS-012 |
| SL-OBS-013 | The system shall emit structured logs when source or destination health changes between green, yellow, and red. | Must | V-SL-OBS-013 |
| SL-OBS-014 | The system shall expose metrics for source folder health, destination folder health, idle watchers, active watchers, and blocked watchers. | Must | V-SL-OBS-014 |
| SL-OBS-015 | The system shall emit structured logs for route tag normalization failures, route preview generation, unmatched source warnings, unmatched destination warnings, and matched destination counts. | Must | V-SL-OBS-015 |
| SL-OBS-016 | The system shall expose metrics for route preview requests, matched destination count, unmatched source count, unmatched destination count, and per-destination delivery outcomes. | Must | V-SL-OBS-016 |
| SL-OBS-017 | The dashboard shall report the active theme name and layout profile in dashboard startup logs and expose them in a visible dashboard footer or settings panel. | Must | V-SL-OBS-017 |
| SL-OBS-018 | The system shall expose metrics for accepted commands, terminal command outcomes, outbox pending count, outbox publish failures, and stage queue lag or eligible job count. | Must | V-SL-OBS-018 |
| SL-OBS-019 | The system shall emit structured logs for command acceptance, command completion, outbox publication success, outbox publication failure, and service reconciliation actions. | Must | V-SL-OBS-019 |

## Log Field Contract

Minimum structured log fields:

```json
{
  "timestamp": "ISO-8601",
  "level": "INFO|WARNING|ERROR|DEBUG",
  "service": "api|dashboard|watcher|validator|processor|delivery|broker",
  "message": "string",
  "job_id": "uuid|null",
  "watcher_id": "uuid|null",
  "event_type": "string|null",
  "state_from": "string|null",
  "state_to": "string|null",
  "error_code": "string|null",
  "duration_ms": "integer|null",
  "folder_role": "source|destination|null",
  "folder_status": "green|yellow|red|null",
  "route_policy": "string|null",
  "route_tags": ["string"],
  "matched_route_tags": ["string"],
  "destination_folder_id": "uuid|null",
  "dashboard_theme": "string|null",
  "dashboard_layout_profile": "string|null"
}
```

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-OBS-NFR-001 | State transition structured log coverage | 100% |
| SL-OBS-NFR-002 | Required log field presence for job-related records | >= 99% |
| SL-OBS-NFR-003 | Summary metrics endpoint p95 latency | <= 300 ms |
| SL-OBS-NFR-004 | Log query endpoint p95 latency for <= 10,000 records | <= 500 ms |
| SL-OBS-NFR-005 | Failed job explainability | 100% include current state + latest error code + latest failed stage |
| SL-OBS-NFR-006 | Folder health status changes logged with role and reason code | 100% |
| SL-OBS-NFR-007 | Watcher idle/active/blocked metric availability | 100% when metrics endpoint is ready |
| SL-OBS-NFR-008 | Route tag and route preview log coverage | 100% of route preview and watcher enablement attempts |
| SL-OBS-NFR-009 | Per-destination delivery outcome metrics coverage | 100% of matched destination delivery attempts |

## Acceptance Criteria

The requirement is accepted when a reviewer can reconstruct a job's lifecycle, folder health history, tag matching decision, matched destination deliveries, dashboard presentation profile, and partial-delivery outcomes from logs, events, database records, metrics, and dashboard views without reading service source code.

## Minimum Prometheus Metric Catalog

| Metric | Type | Labels | Trigger |
|---|---|---|---|
| `stream_lite_api_request_duration_seconds` | histogram | `route`, `method`, `status_code` | Each API request. |
| `stream_lite_file_detected_total` | counter | `watcher_id`, `source_folder_id` | File detection. |
| `stream_lite_job_transition_total` | counter | `from_state`, `to_state` | Job state transition commit. |
| `stream_lite_retry_scheduled_total` | counter | `stage`, `failure_code` | Retry attempt scheduled or executed. |
| `stream_lite_event_publish_total` | counter | `event_type`, `status` | Event publish attempt. |
| `stream_lite_delivery_attempt_total` | counter | `status` | Delivery attempt terminal outcome. |
| `stream_lite_folder_health_status` | gauge | `folder_role`, `folder_id`, `status` | Folder health evaluation. |
| `stream_lite_dashboard_action_total` | counter | `action`, `status` | Streamlit operator action. |
| `stream_lite_api_command_total` | counter | `command_type`, `status` | Command accepted or reaches terminal status. |
| `stream_lite_event_outbox_pending_total` | gauge | `event_type` | Outbox dispatcher scan. |
| `stream_lite_event_publish_total` | counter | `event_type`, `status` | Outbox publish failure. |
| `stream_lite_stage_eligible_jobs` | gauge | `stage` | Reconciliation or scheduler scan of eligible jobs. |

## L2 Contract Decomposition Requirements

These rows decompose observability into log schema, operational log events, metric catalog, summary APIs, and redaction contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-OBS-023 | L2 | SL-OBS-001, SL-OBS-002, SL-OBS-003, SL-OBS-010 | Structured log schema contract | Structured logs shall follow the documented field contract, include nullable job/watcher/file IDs where applicable, use bounded-cardinality event names, and redact secrets/host-only paths. | Must | V-SL-OBS-023 |
| SL-OBS-024 | L2 | SL-OBS-004, SL-OBS-005, SL-OBS-006, SL-OBS-007, SL-OBS-013, SL-OBS-015, SL-OBS-019 | Operational log event contract | State transitions, validation failures, processing/delivery attempts, health changes, route previews, command lifecycle changes, outbox publications, and reconciliation actions shall emit structured logs. | Must | V-SL-OBS-024 |
| SL-OBS-025 | L2 | SL-OBS-009, SL-OBS-011, SL-OBS-014, SL-OBS-016, SL-OBS-018 | Prometheus metric contract | The metrics catalog shall define name, type, labels, owner, trigger, Streamlit use, and requirement IDs; duration metrics shall use seconds and `_duration_seconds`. | Must | V-SL-OBS-025 |
| SL-OBS-026 | L2 | SL-OBS-008, SL-OBS-012 | Dashboard observability summary contract | Log and metrics summary APIs shall return bounded results, deterministic ordering, sanitized messages, aggregate counts, queue lag/eligible counts, and stage durations in seconds. | Must | V-SL-OBS-026 |
| SL-OBS-027 | L2 | SL-OBS-010 | Redaction and exception contract | Unexpected exception logs may include stack traces in service logs, but API/dashboard surfaces shall return sanitized error envelopes with error code, message, and correlation ID only. | Must | V-SL-OBS-027 |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-OBS-020 | L3 | SL-OBS-001, SL-OBS-010 | `stream_lite.observability.logging.emit_structured_log` | The logging helper shall emit JSON logs with required fields, include duration milliseconds only for logs, and reject or redact secrets and host-only raw paths. | V-SL-OBS-020 |
| SL-OBS-021 | L3 | SL-OBS-005, SL-DECOMP-006 | `stream_lite.observability.metrics.record_duration_seconds` | The metrics helper shall record Prometheus duration histograms in seconds and expose metric names ending `_duration_seconds`. | V-SL-OBS-021 |
| SL-OBS-022 | L3 | SL-OBS-012 | `stream_lite.observability.summary.build_metrics_summary` | The metrics summary surface shall aggregate bounded dashboard fields using `stage_durations_seconds`, queue lag, retry counts, delivery counts, watcher counts, and job counts. | V-SL-OBS-022 |
