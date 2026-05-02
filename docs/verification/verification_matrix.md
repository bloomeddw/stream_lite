# Verification Matrix

| Verification ID | Requirement scope | Method | Evidence artifact | Status before implementation |
|---|---|---|---|---|
| V-SL-API-031 | API endpoint contract completeness | docs review + schema lint | `evidence/api_contract_review.md` | planned |
| V-SL-DCT-001 | API schema stubs | JSON schema validation | `evidence/api_schema_validation.json` | planned |
| V-SL-DCT-002 | Event schema files | JSON schema validation + fixture events | `evidence/event_schema_validation.json` | planned |
| V-SL-DCT-003 | Logical data model | docs review + migration traceability later | `evidence/data_model_review.md` | planned |
| V-SL-RUN-ENV-001 | Env var catalog and `.env.example` parity | static lint | `evidence/env_var_lint.json` | planned |
| V-SL-OBS-005 | Metrics catalog coverage | docs review + scrape check later | `evidence/metrics_catalog_review.md` | planned |
| V-SL-RET-001 | Fault/retry/quarantine policy coverage | failure-class review | `evidence/failure_policy_review.md` | planned |
| V-SL-UI-038 | Streamlit control matrix coverage | docs review + manual UI checklist later | `evidence/streamlit_control_review.md` | planned |
| V-SL-VER-001 | Requirement-to-verification mapping | matrix lint | `evidence/verification_matrix_lint.json` | planned |
| V-SL-LIFE-001 | Command persistence before state change | integration test | `evidence/command_lifecycle_test.json` | planned |
| V-SL-LIFE-002 | Job ID before `file.detected` | event-flow test | `evidence/file_detected_contract_test.json` | planned |
| V-SL-EVT-011 | Outbox recovery after broker outage | failure injection | `evidence/outbox_recovery_test.json` | planned |
| V-SL-EVT-015 | Event list API reads persisted lifecycle events | API contract test | `evidence/events_list_api_test.json` | planned |
| V-SL-API-002 | Watcher CRUD route contract | API contract test | `evidence/watcher_api_test.json` | planned |
| V-SL-FWM-026 | Tag route matching | unit + API test | `evidence/route_preview_test.json` | planned |
| V-SL-VAL-016 | Copy-based quarantine | integration test | `evidence/quarantine_copy_test.json` | planned |
| V-SL-PRO-012 | Processing durable before state transition | integration test | `evidence/processing_durability_test.json` | planned |
| V-SL-OUT-010 | Atomic finalized delivery | failure injection | `evidence/delivery_atomicity_test.json` | planned |
| V-SL-OBS-005 | Metrics exposed | Prometheus scrape test | `evidence/metrics_scrape_test.json` | planned |
| V-SL-SEC-001 | Path traversal blocked | security unit/API test | `evidence/path_safety_test.json` | planned |
| V-SL-SPHINX-001 | Static Sphinx build | docs build | `evidence/sphinx_build.txt` | planned |
| V-SL-E2E-001 | End-to-end happy path | Docker Compose E2E | `evidence/e2e_happy_path/summary.md` | planned |
| V-SL-E2E-002 | End-to-end invalid file path | Docker Compose E2E | `evidence/e2e_quarantine/summary.md` | planned |
| V-SL-RET-012 | Manual retry endpoint eligibility and idempotency | API contract + state transition test | `evidence/manual_retry_api_test.json` | planned |
| V-SL-E2E-003 | End-to-end retry path | Docker Compose E2E + failure injection | `evidence/e2e_retry/summary.md` | planned |
| V-SL-REQ-005 | External requirement reference resolution | static docs lint | `evidence/requirement_reference_inventory.md` | planned |
| V-SL-REQ-006 | Missing or adjacent requirement disposition | docs review + worklog review | `evidence/requirement_disposition_review.md` | planned |
| V-SL-REQ-007 | L1/L2/L3 decomposition model | docs review | `evidence/decomposition_model_review.md` | planned |
| V-SL-REQ-008 | L3 backtrace to L1/L2 requirements | static docs lint | `evidence/l3_traceability_lint.json` | planned |
| V-SL-EVT-016 | Active event schema inventory completeness | schema catalog review | `evidence/event_schema_inventory_review.md` | planned |
| V-SL-EVT-017 | Job state changed event contract | event-flow schema test | `evidence/job_state_changed_event_test.json` | planned |
| V-SL-EVT-018 | Detection and registration event ordering | event-flow test | `evidence/detection_registration_order_test.json` | planned |
| V-SL-EVT-019 | Validation versus quarantine event distinction | schema + failure injection test | `evidence/validation_quarantine_event_test.json` | planned |
| V-SL-EVT-020 | Processing event attempt details | integration event-flow test | `evidence/processing_event_contract_test.json` | planned |
| V-SL-EVT-021 | Delivery event destination outcome details | integration event-flow test | `evidence/delivery_event_contract_test.json` | planned |
| V-SL-EVT-022 | Retry scheduled event contract | failure injection event-flow test | `evidence/retry_scheduled_event_test.json` | planned |
| V-SL-EVT-023 | Final job failed event contract | failure injection event-flow test | `evidence/job_failed_event_test.json` | planned |
| V-SL-API-032 | Event list endpoint filter contract | API contract test | `evidence/events_list_filters_test.json` | planned |
| V-SL-API-033 | Async command status lifecycle | API + state transition test | `evidence/async_command_lifecycle_test.json` | planned |
| V-SL-API-034 | Watcher list/detail response completeness | API contract test | `evidence/watcher_response_contract_test.json` | planned |
| V-SL-API-035 | Job detail response completeness | API contract test | `evidence/job_detail_contract_test.json` | planned |
| V-SL-API-036 | Mutation command persistence before enqueue | integration test | `evidence/mutation_command_persistence_test.json` | planned |
| V-SL-API-037 | Command idempotency key behavior | API contract test | `evidence/command_idempotency_test.json` | planned |
| V-SL-API-038 | Deterministic list ordering | API contract test | `evidence/list_ordering_test.json` | planned |
| V-SL-API-039 | Standard error envelope completeness | API contract test | `evidence/error_envelope_test.json` | planned |
| V-SL-API-040 | Endpoint matrix synchronization | static docs lint | `evidence/endpoint_matrix_sync_lint.json` | planned |
| V-SL-API-041 | Health handler implementation trace | unit + API contract test | `evidence/health_handler_test.json` | planned |
| V-SL-API-042 | Dependency health handler implementation trace | unit + API contract test | `evidence/dependency_health_handler_test.json` | planned |
| V-SL-API-043 | Watcher create handler implementation trace | API contract test | `evidence/create_watcher_handler_test.json` | planned |
| V-SL-API-044 | Watcher lifecycle command handler trace | API + state transition test | `evidence/watcher_lifecycle_handler_test.json` | planned |
| V-SL-API-045 | Job detail handler implementation trace | API contract test | `evidence/job_detail_handler_test.json` | planned |
| V-SL-API-046 | Retry handler implementation trace | API + failure injection test | `evidence/retry_handler_test.json` | planned |
| V-SL-API-047 | Command status handler implementation trace | API contract test | `evidence/command_status_handler_test.json` | planned |
| V-SL-API-048 | Event list handler implementation trace | API contract test | `evidence/list_events_handler_test.json` | planned |
| V-SL-API-049 | Folder browse handler implementation trace | API contract test | `evidence/folder_browse_handler_test.json` | planned |
| V-SL-API-050 | Path validation handler implementation trace | API + security test | `evidence/path_validation_handler_test.json` | planned |
| V-SL-FWM-032 | Watcher config persistence trace | unit + repository contract test | `evidence/watcher_config_repository_test.json` | planned |
| V-SL-FWM-033 | Route tag normalization trace | unit test | `evidence/route_tag_normalization_test.json` | planned |
| V-SL-FWM-034 | Route preview matching trace | unit + API contract test | `evidence/route_preview_service_test.json` | planned |
| V-SL-FDI-021 | Source folder scan trace | unit + filesystem simulation test | `evidence/source_scan_test.json` | planned |
| V-SL-FDI-022 | File stability trace | unit + timing simulation test | `evidence/file_stability_test.json` | planned |
| V-SL-FDI-023 | Deduplication key trace | unit test | `evidence/deduplication_key_test.json` | planned |
| V-SL-FDI-024 | Job registration trace | integration event-flow test | `evidence/job_registration_event_test.json` | planned |
| V-SL-VAL-017 | Validation rules trace | unit + schema test | `evidence/validation_rules_test.json` | planned |
| V-SL-VAL-018 | Quarantine copy trace | integration filesystem test | `evidence/quarantine_copy_surface_test.json` | planned |
| V-SL-VAL-019 | Validation stage completion trace | integration event-flow test | `evidence/validation_stage_completion_test.json` | planned |
| V-SL-EVT-024 | Event outbox enqueue trace | schema + repository test | `evidence/outbox_enqueue_test.json` | planned |
| V-SL-EVT-025 | Event dispatcher publish trace | failure injection test | `evidence/outbox_dispatcher_test.json` | planned |
| V-SL-EVT-026 | Event repository list trace | repository + API contract test | `evidence/event_repository_list_test.json` | planned |
| V-SL-PRO-021 | Processing job claim trace | integration concurrency test | `evidence/processing_claim_test.json` | planned |
| V-SL-PRO-022 | Demo Spark transform trace | integration processing test | `evidence/demo_spark_transform_test.json` | planned |
| V-SL-PRO-023 | Processing completion trace | integration event-flow test | `evidence/processing_completion_test.json` | planned |
| V-SL-OUT-021 | Delivery target resolution trace | unit + route matching test | `evidence/delivery_target_resolution_test.json` | planned |
| V-SL-OUT-022 | Filesystem delivery trace | integration filesystem test | `evidence/filesystem_delivery_test.json` | planned |
| V-SL-OUT-023 | Delivery final state trace | unit + state transition test | `evidence/delivery_final_state_test.json` | planned |
| V-SL-RET-013 | Retry scheduling trace | unit test | `evidence/retry_schedule_test.json` | planned |
| V-SL-RET-014 | Retry exhaustion trace | failure injection test | `evidence/retry_exhaustion_test.json` | planned |
| V-SL-RET-015 | Manual retry command trace | API + idempotency test | `evidence/manual_retry_command_test.json` | planned |
| V-SL-UI-039 | Command center render trace | Streamlit manual check | `evidence/streamlit_command_center_check.md` | planned |
| V-SL-UI-040 | Presentation config fallback trace | Streamlit manual + API test | `evidence/presentation_config_fallback_test.md` | planned |
| V-SL-UI-041 | Dashboard command tracking trace | Streamlit manual + API test | `evidence/dashboard_command_tracking_test.md` | planned |
| V-SL-OBS-020 | Structured log helper trace | unit test | `evidence/structured_log_helper_test.json` | planned |
| V-SL-OBS-021 | Duration seconds metrics trace | Prometheus scrape + unit test | `evidence/duration_seconds_metric_test.json` | planned |
| V-SL-OBS-022 | Metrics summary trace | API contract test | `evidence/metrics_summary_surface_test.json` | planned |
| V-DATA-MIGRATION-001 | Migration design review | docs review | `evidence/data_migration_plan_review.md` | planned |
| V-DATA-MIGRATION-002 | Migration upgrade/downgrade behavior | future Alembic test | `evidence/alembic_upgrade_downgrade.log` | planned |
| V-DATA-MIGRATION-003 | Migration design contract lint | static lint | `evidence/migration_design_lint.json` | planned |
| V-SL-DECOMP-001 | SL-DECOMP-001 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-001_review.md` | planned |
| V-SL-DECOMP-002 | SL-DECOMP-002 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-002_review.md` | planned |
| V-SL-DECOMP-003 | SL-DECOMP-003 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-003_review.md` | planned |
| V-SL-DECOMP-004 | SL-DECOMP-004 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-004_review.md` | planned |
| V-SL-DECOMP-005 | SL-DECOMP-005 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-005_review.md` | planned |
| V-SL-DECOMP-006 | SL-DECOMP-006 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-006_review.md` | planned |
| V-SL-DECOMP-007 | SL-DECOMP-007 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-007_review.md` | planned |
| V-SL-DECOMP-008 | SL-DECOMP-008 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-008_review.md` | planned |
| V-SL-DECOMP-009 | SL-DECOMP-009 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-009_review.md` | planned |
| V-SL-DECOMP-010 | SL-DECOMP-010 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-decomp-010_review.md` | planned |
| V-SL-RUN-019 | SL-RUN-019 L2 Docker Compose service contract | docs review + contract lint | `evidence/l2_contracts/sl-run-019_review.md` | planned |
| V-SL-RUN-020 | SL-RUN-020 L2 Runtime configuration loader contract | docs review + contract lint | `evidence/l2_contracts/sl-run-020_review.md` | planned |
| V-SL-RUN-021 | SL-RUN-021 L2 Volume ownership contract | docs review + contract lint | `evidence/l2_contracts/sl-run-021_review.md` | planned |
| V-SL-RUN-022 | SL-RUN-022 L2 Readiness response contract | docs review + contract lint | `evidence/l2_contracts/sl-run-022_review.md` | planned |
| V-SL-RUN-023 | SL-RUN-023 L2 Unsupported profile contract | docs review + contract lint | `evidence/l2_contracts/sl-run-023_review.md` | planned |
| V-SL-FWM-035 | SL-FWM-035 L2 Watcher configuration contract | docs review + contract lint | `evidence/l2_contracts/sl-fwm-035_review.md` | planned |
| V-SL-FWM-036 | SL-FWM-036 L2 Watcher lifecycle command contract | docs review + contract lint | `evidence/l2_contracts/sl-fwm-036_review.md` | planned |
| V-SL-FWM-037 | SL-FWM-037 L2 Folder reachability contract | docs review + contract lint | `evidence/l2_contracts/sl-fwm-037_review.md` | planned |
| V-SL-FWM-038 | SL-FWM-038 L2 Route tag normalization contract | docs review + contract lint | `evidence/l2_contracts/sl-fwm-038_review.md` | planned |
| V-SL-FWM-039 | SL-FWM-039 L2 Route preview contract | docs review + contract lint | `evidence/l2_contracts/sl-fwm-039_review.md` | planned |
| V-SL-FDI-025 | SL-FDI-025 L2 Source scan eligibility contract | docs review + contract lint | `evidence/l2_contracts/sl-fdi-025_review.md` | planned |
| V-SL-FDI-026 | SL-FDI-026 L2 File stability contract | docs review + contract lint | `evidence/l2_contracts/sl-fdi-026_review.md` | planned |
| V-SL-FDI-027 | SL-FDI-027 L2 File identity contract | docs review + contract lint | `evidence/l2_contracts/sl-fdi-027_review.md` | planned |
| V-SL-FDI-028 | SL-FDI-028 L2 Duplicate suppression contract | docs review + contract lint | `evidence/l2_contracts/sl-fdi-028_review.md` | planned |
| V-SL-FDI-029 | SL-FDI-029 L2 Job registration handoff contract | docs review + contract lint | `evidence/l2_contracts/sl-fdi-029_review.md` | planned |
| V-SL-VAL-020 | SL-VAL-020 L2 Validation rule contract | docs review + contract lint | `evidence/l2_contracts/sl-val-020_review.md` | planned |
| V-SL-VAL-021 | SL-VAL-021 L2 Validation outcome contract | docs review + contract lint | `evidence/l2_contracts/sl-val-021_review.md` | planned |
| V-SL-VAL-022 | SL-VAL-022 L2 Quarantine record contract | docs review + contract lint | `evidence/l2_contracts/sl-val-022_review.md` | planned |
| V-SL-VAL-023 | SL-VAL-023 L2 Quarantine filesystem contract | docs review + contract lint | `evidence/l2_contracts/sl-val-023_review.md` | planned |
| V-SL-VAL-024 | SL-VAL-024 L2 Validation event/log contract | docs review + contract lint | `evidence/l2_contracts/sl-val-024_review.md` | planned |
| V-SL-JOB-025 | SL-JOB-025 L2 Job identity contract | docs review + contract lint | `evidence/l2_contracts/sl-job-025_review.md` | planned |
| V-SL-JOB-026 | SL-JOB-026 L2 State transition contract | docs review + contract lint | `evidence/l2_contracts/sl-job-026_review.md` | planned |
| V-SL-JOB-027 | SL-JOB-027 L2 Stage attempt contract | docs review + contract lint | `evidence/l2_contracts/sl-job-027_review.md` | planned |
| V-SL-JOB-028 | SL-JOB-028 L2 Command and outbox durability contract | docs review + contract lint | `evidence/l2_contracts/sl-job-028_review.md` | planned |
| V-SL-JOB-029 | SL-JOB-029 L2 Stage ownership lease contract | docs review + contract lint | `evidence/l2_contracts/sl-job-029_review.md` | planned |
| V-SL-JOB-030 | SL-JOB-030 L2 Job query contract | docs review + contract lint | `evidence/l2_contracts/sl-job-030_review.md` | planned |
| V-SL-PRO-024 | SL-PRO-024 L2 Processing engine selection contract | docs review + contract lint | `evidence/l2_contracts/sl-pro-024_review.md` | planned |
| V-SL-PRO-025 | SL-PRO-025 L2 Processing claim contract | docs review + contract lint | `evidence/l2_contracts/sl-pro-025_review.md` | planned |
| V-SL-PRO-026 | SL-PRO-026 L2 Processing input contract | docs review + contract lint | `evidence/l2_contracts/sl-pro-026_review.md` | planned |
| V-SL-PRO-027 | SL-PRO-027 L2 Demo transform output contract | docs review + contract lint | `evidence/l2_contracts/sl-pro-027_review.md` | planned |
| V-SL-PRO-028 | SL-PRO-028 L2 Processing completion contract | docs review + contract lint | `evidence/l2_contracts/sl-pro-028_review.md` | planned |
| V-SL-PRO-029 | SL-PRO-029 L2 Processing failure contract | docs review + contract lint | `evidence/l2_contracts/sl-pro-029_review.md` | planned |
| V-SL-OUT-024 | SL-OUT-024 L2 Delivery target resolution contract | docs review + contract lint | `evidence/l2_contracts/sl-out-024_review.md` | planned |
| V-SL-OUT-025 | SL-OUT-025 L2 Atomic filesystem delivery contract | docs review + contract lint | `evidence/l2_contracts/sl-out-025_review.md` | planned |
| V-SL-OUT-026 | SL-OUT-026 L2 Per-destination attempt contract | docs review + contract lint | `evidence/l2_contracts/sl-out-026_review.md` | planned |
| V-SL-OUT-027 | SL-OUT-027 L2 Partial delivery contract | docs review + contract lint | `evidence/l2_contracts/sl-out-027_review.md` | planned |
| V-SL-OUT-028 | SL-OUT-028 L2 Delivery manifest contract | docs review + contract lint | `evidence/l2_contracts/sl-out-028_review.md` | planned |
| V-SL-OUT-029 | SL-OUT-029 L2 Delivery failure and final-state contract | docs review + contract lint | `evidence/l2_contracts/sl-out-029_review.md` | planned |
| V-SL-RET-016 | SL-RET-016 L2 Retry classification contract | docs review + contract lint | `evidence/l2_contracts/sl-ret-016_review.md` | planned |
| V-SL-RET-017 | SL-RET-017 L2 Retry backoff contract | docs review + contract lint | `evidence/l2_contracts/sl-ret-017_review.md` | planned |
| V-SL-RET-018 | SL-RET-018 L2 Retry execution contract | docs review + contract lint | `evidence/l2_contracts/sl-ret-018_review.md` | planned |
| V-SL-RET-019 | SL-RET-019 L2 Retry exhaustion contract | docs review + contract lint | `evidence/l2_contracts/sl-ret-019_review.md` | planned |
| V-SL-RET-020 | SL-RET-020 L2 Manual retry contract | docs review + contract lint | `evidence/l2_contracts/sl-ret-020_review.md` | planned |
| V-SL-API-022 | SL-API-022 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-022_review.md` | planned |
| V-SL-API-023 | SL-API-023 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-023_review.md` | planned |
| V-SL-API-024 | SL-API-024 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-024_review.md` | planned |
| V-SL-API-025 | SL-API-025 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-025_review.md` | planned |
| V-SL-API-026 | SL-API-026 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-026_review.md` | planned |
| V-SL-API-027 | SL-API-027 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-027_review.md` | planned |
| V-SL-API-028 | SL-API-028 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-028_review.md` | planned |
| V-SL-API-029 | SL-API-029 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-029_review.md` | planned |
| V-SL-API-030 | SL-API-030 L2 Must | docs review + contract lint | `evidence/l2_contracts/sl-api-030_review.md` | planned |
| V-SL-UI-042 | SL-UI-042 L2 Dashboard data-source contract | docs review + contract lint | `evidence/l2_contracts/sl-ui-042_review.md` | planned |
| V-SL-UI-043 | SL-UI-043 L2 Dashboard mutation control contract | docs review + contract lint | `evidence/l2_contracts/sl-ui-043_review.md` | planned |
| V-SL-UI-044 | SL-UI-044 L2 Async command feedback contract | docs review + contract lint | `evidence/l2_contracts/sl-ui-044_review.md` | planned |
| V-SL-UI-045 | SL-UI-045 L2 Presentation configuration contract | docs review + contract lint | `evidence/l2_contracts/sl-ui-045_review.md` | planned |
| V-SL-UI-046 | SL-UI-046 L2 Dashboard error and empty-state contract | docs review + contract lint | `evidence/l2_contracts/sl-ui-046_review.md` | planned |
| V-SL-OBS-023 | SL-OBS-023 L2 Structured log schema contract | docs review + contract lint | `evidence/l2_contracts/sl-obs-023_review.md` | planned |
| V-SL-OBS-024 | SL-OBS-024 L2 Operational log event contract | docs review + contract lint | `evidence/l2_contracts/sl-obs-024_review.md` | planned |
| V-SL-OBS-025 | SL-OBS-025 L2 Prometheus metric contract | docs review + contract lint | `evidence/l2_contracts/sl-obs-025_review.md` | planned |
| V-SL-OBS-026 | SL-OBS-026 L2 Dashboard observability summary contract | docs review + contract lint | `evidence/l2_contracts/sl-obs-026_review.md` | planned |
| V-SL-OBS-027 | SL-OBS-027 L2 Redaction and exception contract | docs review + contract lint | `evidence/l2_contracts/sl-obs-027_review.md` | planned |
| V-SL-SEC-013 | SL-SEC-013 L2 Path allowlist contract | docs review + contract lint | `evidence/l2_contracts/sl-sec-013_review.md` | planned |
| V-SL-SEC-014 | SL-SEC-014 L2 Path normalization and message contract | docs review + contract lint | `evidence/l2_contracts/sl-sec-014_review.md` | planned |
| V-SL-SEC-015 | SL-SEC-015 L2 Local trusted mode boundary contract | docs review + contract lint | `evidence/l2_contracts/sl-sec-015_review.md` | planned |
| V-SL-SEC-016 | SL-SEC-016 L2 Secret handling contract | docs review + contract lint | `evidence/l2_contracts/sl-sec-016_review.md` | planned |
| V-SL-SEC-017 | SL-SEC-017 L2 Container user contract | docs review + contract lint | `evidence/l2_contracts/sl-sec-017_review.md` | planned |
| V-SL-VER-027 | SL-VER-027 L2 Requirement coverage contract | docs review + contract lint | `evidence/l2_contracts/sl-ver-027_review.md` | planned |
| V-SL-VER-028 | SL-VER-028 L2 Evidence artifact contract | docs review + contract lint | `evidence/l2_contracts/sl-ver-028_review.md` | planned |
| V-SL-VER-029 | SL-VER-029 L2 Acceptance test scenario contract | docs review + contract lint | `evidence/l2_contracts/sl-ver-029_review.md` | planned |
| V-SL-VER-030 | SL-VER-030 L2 Manual validation contract | docs review + contract lint | `evidence/l2_contracts/sl-ver-030_review.md` | planned |
| V-SL-VER-031 | SL-VER-031 L2 Release readiness gate contract | docs review + contract lint | `evidence/l2_contracts/sl-ver-031_review.md` | planned |
| V-SL-BND-018 | SL-BND-018 L2 Service ownership contract | docs review + contract lint | `evidence/l2_contracts/sl-bnd-018_review.md` | planned |
| V-SL-BND-019 | SL-BND-019 L2 Cross-service read contract | docs review + contract lint | `evidence/l2_contracts/sl-bnd-019_review.md` | planned |
| V-SL-BND-020 | SL-BND-020 L2 Command handoff contract | docs review + contract lint | `evidence/l2_contracts/sl-bnd-020_review.md` | planned |
| V-SL-BND-021 | SL-BND-021 L2 Event handoff contract | docs review + contract lint | `evidence/l2_contracts/sl-bnd-021_review.md` | planned |
| V-SL-BND-022 | SL-BND-022 L2 Boundary failure and reconciliation contract | docs review + contract lint | `evidence/l2_contracts/sl-bnd-022_review.md` | planned |
| V-SL-DCT-020 | SL-DCT-020 L2 Contract inventory contract | docs review + contract lint | `evidence/l2_contracts/sl-dct-020_review.md` | planned |
| V-SL-DCT-021 | SL-DCT-021 L2 Schema compatibility contract | docs review + contract lint | `evidence/l2_contracts/sl-dct-021_review.md` | planned |
| V-SL-DCT-022 | SL-DCT-022 L2 Example fixture contract | docs review + contract lint | `evidence/l2_contracts/sl-dct-022_review.md` | planned |
| V-SL-DCT-023 | SL-DCT-023 L2 Field semantics contract | docs review + contract lint | `evidence/l2_contracts/sl-dct-023_review.md` | planned |
| V-SL-DCT-024 | SL-DCT-024 L2 Contract lint contract | docs review + contract lint | `evidence/l2_contracts/sl-dct-024_review.md` | planned |
| V-SL-LIFE-021 | SL-LIFE-021 L2 Lifecycle stage contract | docs review + contract lint | `evidence/l2_contracts/sl-life-021_review.md` | planned |
| V-SL-LIFE-022 | SL-LIFE-022 L2 Durable handoff contract | docs review + contract lint | `evidence/l2_contracts/sl-life-022_review.md` | planned |
| V-SL-LIFE-023 | SL-LIFE-023 L2 Backpressure contract | docs review + contract lint | `evidence/l2_contracts/sl-life-023_review.md` | planned |
| V-SL-LIFE-024 | SL-LIFE-024 L2 Idempotency contract | docs review + contract lint | `evidence/l2_contracts/sl-life-024_review.md` | planned |
| V-SL-LIFE-025 | SL-LIFE-025 L2 Restart recovery contract | docs review + contract lint | `evidence/l2_contracts/sl-life-025_review.md` | planned |
| V-SL-DCT-025 | SL-DCT-025 L2 API schema parity lint contract | contract lint | `evidence/contract_lint/api_schema_parity.txt` | planned |
| V-SL-DCT-026 | SL-DCT-026 L2 Event schema parity lint contract | contract lint | `evidence/contract_lint/event_schema_parity.txt` | planned |
| V-SL-DCT-027 | SL-DCT-027 L2 Environment variable parity lint contract | contract lint | `evidence/contract_lint/env_var_parity.txt` | planned |
| V-SL-DCT-028 | SL-DCT-028 L2 Metrics catalog parity lint contract | contract lint | `evidence/contract_lint/metrics_catalog_parity.txt` | planned |
| V-SL-JOB-031 | SL-JOB-031 L3 watchers repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-031_review.md` | planned |
| V-SL-JOB-032 | SL-JOB-032 L3 watcher_sources repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-032_review.md` | planned |
| V-SL-JOB-033 | SL-JOB-033 L3 watcher_destinations repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-033_review.md` | planned |
| V-SL-JOB-034 | SL-JOB-034 L3 watcher_route_matches repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-034_review.md` | planned |
| V-SL-JOB-035 | SL-JOB-035 L3 files repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-035_review.md` | planned |
| V-SL-JOB-036 | SL-JOB-036 L3 jobs repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-036_review.md` | planned |
| V-SL-JOB-037 | SL-JOB-037 L3 job_state_history repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-037_review.md` | planned |
| V-SL-JOB-038 | SL-JOB-038 L3 validation_attempts repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-038_review.md` | planned |
| V-SL-JOB-039 | SL-JOB-039 L3 quarantine_records repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-039_review.md` | planned |
| V-SL-JOB-040 | SL-JOB-040 L3 processing_attempts repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-040_review.md` | planned |
| V-SL-JOB-041 | SL-JOB-041 L3 output_manifests repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-041_review.md` | planned |
| V-SL-JOB-042 | SL-JOB-042 L3 delivery_attempts repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-042_review.md` | planned |
| V-SL-JOB-043 | SL-JOB-043 L3 retry_schedules repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-043_review.md` | planned |
| V-SL-JOB-044 | SL-JOB-044 L3 control_commands repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-044_review.md` | planned |
| V-SL-JOB-045 | SL-JOB-045 L3 idempotency_keys repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-045_review.md` | planned |
| V-SL-JOB-046 | SL-JOB-046 L3 stage_ownership_claims repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-046_review.md` | planned |
| V-SL-JOB-047 | SL-JOB-047 L3 duplicate_suppression_observations repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-047_review.md` | planned |
| V-SL-JOB-048 | SL-JOB-048 L3 event_outbox repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-048_review.md` | planned |
| V-SL-JOB-049 | SL-JOB-049 L3 event_offsets repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-049_review.md` | planned |
| V-SL-JOB-050 | SL-JOB-050 L3 operational_log_summaries repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-050_review.md` | planned |
| V-SL-JOB-051 | SL-JOB-051 L3 health_observations repository | docs review + repository contract test | `evidence/l3_persistence/sl-job-051_review.md` | planned |
| V-SL-DCT-029 | SL-DCT-029 | Contract/schema test | Run `python tools/validate_schema_examples.py --write-evidence` and confirm enum invalid fixtures are rejected. | `docs/verification/evidence/schema_fixture_validation.md` |
| V-SL-DCT-030 | SL-DCT-030 | Contract/schema test | Run `python tools/validate_schema_examples.py --write-evidence` and confirm timestamp invalid fixtures are rejected. | `docs/verification/evidence/schema_fixture_validation.md` |
| V-SL-DCT-031 | SL-DCT-031 | Contract/schema test | Run `python tools/validate_schema_examples.py --write-evidence` and confirm path-safety invalid fixtures are rejected. | `docs/verification/evidence/schema_fixture_validation.md` |
| V-SL-DCT-032 | SL-DCT-032 | Static contract lint | Run `python -S tools/contract_lint.py --write-inventory` and confirm artifact inventory/schema/example parity passes. | `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md` |
| V-SL-DCT-033 | SL-DCT-033 | Static contract lint | Run `python -S tools/contract_lint.py --write-inventory` and confirm deep invalid fixture coverage checks pass. | `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md` |
