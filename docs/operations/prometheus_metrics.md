# Prometheus Metrics Catalog

All metrics shall use prefix `stream_lite_`. Labels shall use bounded cardinality and shall not include raw file paths, host paths, secrets, or unbounded error messages. Duration histograms shall use seconds and names ending in `_duration_seconds`.

| Metric | Type | Labels | Owner | Trigger | Dashboard use | Threshold/target | Requirements |
|---|---|---|---|---|---|---|---|
| `stream_lite_api_request_duration_seconds` | histogram | `route`, `method`, `status_code` | API | Every API response | API health panel | p95 route targets from REQ-010 | SL-OBS-005 |
| `stream_lite_api_request_total` | counter | `route`, `method`, `status_code` | API | Every API response | API activity summary | n/a | SL-OBS-005 |
| `stream_lite_api_command_total` | counter | `command_type`, `status` | API | Command mutation accepted or rejected | Command status panel | accepted/rejected visible | SL-LIFE-015 |
| `stream_lite_route_preview_total` | counter | `status` | API | Route preview request | Routing panel | invalid tags visible | SL-FWM-026 |
| `stream_lite_retry_command_total` | counter | `status` | API/retry scheduler | Manual retry command accepted or rejected | Retry panel | rejected reasons visible | SL-RET-012 |
| `stream_lite_path_validation_total` | counter | `purpose`, `status`, `reason_code` | API | Path validation request | Folder configuration panel | invalid paths visible | SL-SEC-001 |
| `stream_lite_api_dependency_status` | gauge | `dependency` | API | Health dependency check | Health panel | `1` ready, `0` unavailable | SL-RUN-013 |
| `stream_lite_watcher_status` | gauge | `watcher_id`, `status` | watcher | Watcher status update | Folder/watch panel | one active status per watcher | SL-FWM-019 |
| `stream_lite_folder_health_status` | gauge | `folder_role`, `status`, `reason_code` | API/watcher | Folder validation or health refresh | Folder health dots | green/yellow/red correctness 100% | SL-FWM-018 |
| `stream_lite_file_detected_total` | counter | `watcher_id` | watcher | Stable candidate observed | File activity | n/a | SL-FDI-004 |
| `stream_lite_duplicate_suppressed_total` | counter | `watcher_id` | watcher | Duplicate suppressed | Duplicate panel | n/a | SL-LIFE-013 |
| `stream_lite_job_state_total` | gauge | `state` | API | Summary refresh | Job count cards | n/a | SL-OBS-009 |
| `stream_lite_job_transition_total` | counter | `from_state`, `to_state`, `actor_service` | workers | State transition committed | Lifecycle audit | n/a | SL-LIFE-009 |
| `stream_lite_stage_duration_seconds` | histogram | `stage`, `status` | workers | Stage attempt completion | Stage duration cards | stage targets from reqs | SL-OBS-009 |
| `stream_lite_event_outbox_pending_total` | gauge | `event_type` | event dispatcher | Outbox poll | Broker health | should drain under normal load | SL-EVT-011 |
| `stream_lite_event_publish_total` | counter | `event_type`, `status` | event dispatcher | Publish attempt | Event panel | errors visible | SL-EVT-011 |
| `stream_lite_event_consumer_lag` | gauge | `consumer_group`, `stream_name` | consumers | Consumer poll | Queue lag panel | visible for active stages | SL-LIFE-019 |
| `stream_lite_stage_eligible_jobs` | gauge | `stage` | workers | Reconciliation query | Backpressure panel | visible for validation/processing/delivery/retry/outbox | SL-LIFE-019 |
| `stream_lite_retry_scheduled_total` | counter | `stage`, `failure_class` | retry scheduler | Retry scheduled | Retry panel | n/a | SL-RET-004 |
| `stream_lite_retry_exhausted_total` | counter | `stage`, `failure_class` | retry scheduler | Retry exhausted | Retry/failure panel | n/a | SL-RET-009 |
| `stream_lite_validation_failure_total` | counter | `reason_code` | validator | Validation rejects file | Validation failures panel | n/a | SL-VAL-010 |
| `stream_lite_quarantine_copy_total` | counter | `status`, `reason_code` | validator | Quarantine copy attempt | Quarantine panel | source modification count 0 | SL-VAL-016 |
| `stream_lite_processing_attempt_total` | counter | `engine`, `status` | processor | Processing attempt completion | Processing panel | n/a | SL-PRO-005 |
| `stream_lite_delivery_attempt_total` | counter | `status` | delivery | Per-destination delivery attempt | Output delivery panel | n/a | SL-OUT-006 |
| `stream_lite_output_manifest_total` | counter | `status` | delivery | Manifest finalized | Output panel | n/a | SL-OUT-010 |
| `stream_lite_dashboard_action_total` | counter | `action`, `status` | dashboard | Operator action submitted | Operator action panel | n/a | SL-UI-001 |
| `stream_lite_error_total` | counter | `service`, `error_code` | all | Handled error emitted | Error summary | n/a | SL-OBS-010 |
