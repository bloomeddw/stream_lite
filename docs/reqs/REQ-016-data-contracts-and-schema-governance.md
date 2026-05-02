# REQ-016: Data Contracts and Schema Governance Requirements

## Capability Intent

Stream Lite shall define versioned data contracts for API payloads, persisted operational records, event messages, output manifests, quarantine records, dashboard presentation configuration, and verification evidence before implementation. These contracts shall prevent implementation agents from inventing incompatible field names, optionality, state values, or schema evolution behavior.

## Scope

In scope for v0.1:
- API request and response schema names and required fields.
- Event schema envelope and payload requirements.
- PostgreSQL logical data model requirements.
- Output, delivery, quarantine, dashboard configuration, and evidence schemas.
- Schema versioning, validation, and compatibility behavior.

Out of scope for v0.1:
- Public external API compatibility guarantees.
- Cross-language generated client SDKs.
- Production schema registry service.

## Contract Governance Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-DCT-001 | Every API schema used by a documented endpoint shall have a named request or response contract under `docs/api/` or `stream_lite/schemas/api/` before endpoint implementation. | Must | V-SL-DCT-001 |
| SL-DCT-002 | Every event type listed in REQ-005 shall have a versioned schema under `docs/schemas/events/` or `stream_lite/schemas/events/` before producer or consumer implementation. | Must | V-SL-DCT-002 |
| SL-DCT-003 | Every persisted operational table shall have a logical schema entry documenting table name, primary key, required columns, allowed enum values, foreign keys, indexes needed for MVP queries, retention expectation, and owning service. | Must | V-SL-DCT-003 |
| SL-DCT-004 | All schemas shall include `schema_version` using semantic version format `major.minor.patch` or integer event schema version format `v1`; each document shall choose one format and state compatibility rules. | Must | V-SL-DCT-004 |
| SL-DCT-005 | Event producers shall emit only fields defined by the active event schema unless the field name begins with `x_` and the schema permits extension fields. | Must | V-SL-DCT-005 |
| SL-DCT-006 | Event consumers shall ignore unknown `x_` extension fields and shall reject missing required fields with `SCHEMA_CONTRACT_VIOLATION`. | Must | V-SL-DCT-006 |
| SL-DCT-007 | API responses shall use stable enum values for job states, watcher lifecycle states, operational health states, retry statuses, validation reason codes, and delivery statuses. | Must | V-SL-DCT-007 |
| SL-DCT-008 | File, job, watcher, attempt, destination, and event identifiers shall use UUID strings unless a schema explicitly defines a different identifier type. | Must | V-SL-DCT-008 |
| SL-DCT-009 | All timestamp fields in API, event, database logical schemas, manifests, and evidence files shall be RFC 3339 UTC strings with `Z` suffix when serialized outside PostgreSQL. | Must | V-SL-DCT-009 |
| SL-DCT-010 | All path fields exposed to operators shall use sanitized container-relative or mount-relative display paths and shall not expose host-only absolute paths. | Must | V-SL-DCT-010 |
| SL-DCT-011 | Output manifests shall have a versioned schema that includes `job_id`, `watcher_id`, `source_sha256`, `processing_summary_locator`, destination outcomes, produced output paths, timestamps, and status. | Must | V-SL-DCT-011 |
| SL-DCT-012 | Quarantine records shall have a versioned schema that includes `job_id`, `watcher_id`, source display path, quarantine locator, reason codes, copy status, timestamps, and operator message. | Must | V-SL-DCT-012 |
| SL-DCT-013 | Dashboard presentation configuration shall have a versioned YAML schema defining required theme tokens, status-dot tokens, layout profiles, section IDs, refresh interval, and fallback behavior. | Must | V-SL-DCT-013 |
| SL-DCT-014 | Verification evidence files shall have machine-readable schemas for `case_manifest.json`, `comparison.json`, and `summary.md` and `metadata_sidecar.json`. | Must | V-SL-DCT-014 |
| SL-DCT-015 | A schema compatibility check shall run before acceptance and shall fail if a required field is removed, an enum value is renamed, or a required field changes type without a major version change. | Must | V-SL-DCT-015 |
| SL-DCT-016 | Control-plane schemas shall distinguish command acceptance from command completion using explicit fields `command_id`, `accepted_at`, `status`, and `result_locator` when asynchronous commands return `202`. | Must | V-SL-DCT-016 |
| SL-DCT-017 | Command records shall have a versioned schema with `command_id`, `command_type`, `target_resource_type`, `target_resource_id`, `requested_by`, `requested_at`, `status`, `idempotency_key`, `operator_reason`, `completed_at`, `result_locator`, and `error_code`. | Must | V-SL-DCT-017 |
| SL-DCT-018 | Event outbox records shall have a versioned schema with `outbox_id`, `event_id`, `event_type`, `stream_name`, `job_id`, `watcher_id`, `payload`, `status`, `created_at`, `published_at`, `publish_attempt_count`, and `last_error_code`. | Must | V-SL-DCT-018 |
| SL-DCT-019 | Duplicate-suppression observations shall have a versioned schema with `observation_id`, `existing_job_id`, `watcher_id`, `source_folder_id`, `source_display_path`, `byte_size`, `content_hash`, `observed_at`, and reason code `DUPLICATE_SUPPRESSED`. | Must | V-SL-DCT-019 |

## Required Contract Inventory

| Contract area | Minimum contract names | Owning requirement |
|---|---|---|
| Watchers API | `WatcherCreateRequest`, `WatcherPatchRequest`, `WatcherDetailResponse`, `WatcherListResponse`, `WatcherCommandResponse`, `RoutePreviewResponse` | REQ-010 |
| Jobs API | `JobListResponse`, `JobDetailResponse`, `JobHistoryResponse`, `JobRetryRequest`, `JobRetryResponse` | REQ-010 |
| Commands API | `CommandStatusResponse`, `CommandAcceptedResponse` | REQ-010 |
| Files API | `FolderBrowseResponse`, `PathValidationRequest`, `PathValidationResponse` | REQ-010 |
| Config API | `DashboardPresentationResponse` | REQ-010, REQ-011 |
| Events | `file.detected.v1`, `file.stable.v1`, `job.registered.v1`, `job.state_changed.v1`, `file.validated.v1`, `file.quarantined.v1`, `processing.started.v1`, `processing.completed.v1`, `processing.failed.v1`, `delivery.started.v1`, `delivery.completed.v1`, `delivery.failed.v1`, `retry.scheduled.v1`, `job.completed.v1`, `job.failed.v1` | REQ-005 |
| Database logical model | `watchers`, `watcher_sources`, `watcher_destinations`, `jobs`, `job_state_history`, `validation_attempts`, `processing_attempts`, `delivery_attempts`, `retry_schedules`, `event_outbox`, `event_offsets`, `idempotency_keys`, `stage_ownership_claims`, `control_commands`, `duplicate_suppression_observations`, `operational_log_summaries` | REQ-006 |
| Artifacts | `processing_summary.json`, `output_manifest.json`, `quarantine_record.json`, verification evidence files | REQ-004, REQ-007, REQ-008, REQ-014 |

## Minimum Field Semantics

| Field class | Requirement |
|---|---|
| Identifiers | UUID string, lowercase canonical form preferred, never reused after deletion. |
| Timestamps | RFC 3339 UTC serialized strings; PostgreSQL may store native timestamp with time zone. |
| Durations | Numeric seconds in fields ending `_duration_seconds` or `duration_seconds`; structured logs may use `duration_ms`. |
| Hashes | SHA-256 hex strings in fields ending `_sha256` or `content_hash`. |
| States | Uppercase snake-case for job states; lowercase snake-case for event type names. |
| Error codes | Uppercase snake-case in API and persisted failure records. |
| Metrics labels | Lowercase snake-case with bounded cardinality. |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-DCT-NFR-001 | Documented schemas for active API endpoints before implementation | 100% |
| SL-DCT-NFR-002 | Documented schemas for active event types before implementation | 100% |
| SL-DCT-NFR-003 | Schema validation pass rate for fixture API responses and events | 100% |
| SL-DCT-NFR-004 | Unknown required field removals without major version change | 0 |
| SL-DCT-NFR-005 | Host-only absolute paths exposed in operator-facing schemas | 0 |

## L2 Contract Decomposition Requirements

These rows decompose schema governance into inventory, compatibility, examples, field semantics, and lint contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-DCT-020 | L2 | SL-DCT-001, SL-DCT-002, SL-DCT-003 | Contract inventory contract | The contract inventory shall list active API schemas, event schemas, artifact schemas, examples, owning requirement IDs, owner services, and compatibility status. | Must | V-SL-DCT-020 |
| SL-DCT-021 | L2 | SL-DCT-004, SL-DCT-005, SL-DCT-006 | Schema compatibility contract | API and event schema changes shall identify compatibility impact, require schema version changes when compatibility is broken, and document affected producers/consumers/fixtures. | Must | V-SL-DCT-021 |
| SL-DCT-022 | L2 | SL-DCT-007, SL-DCT-008, SL-DCT-009 | Example fixture contract | Each active API and event schema shall have valid and invalid examples under `schemas/examples`; invalid examples shall at minimum prove missing-required-field rejection, with enum, timestamp, and path-safety invalid fixtures added for high-risk schema fields before implementation tests are generated. | Must | V-SL-DCT-022 |
| SL-DCT-023 | L2 | SL-DCT-010, SL-DCT-011, SL-DCT-012 | Field semantics contract | Required fields, nullable fields, enums, timestamps, ID formats, path locators, and operator-safe messages shall be consistent across API docs, schemas, event docs, and data model docs. | Must | V-SL-DCT-023 |
| SL-DCT-024 | L2 | SL-DCT-013, SL-DCT-014, SL-DCT-015, SL-DCT-019 | Contract lint contract | Static lint shall check JSON parseability, example presence, requirement references, duplicate requirement IDs, duration metric naming, and schema/example parity before implementation milestones. | Must | V-SL-DCT-024 |
| SL-DCT-025 | L2 | SL-DCT-001, SL-DCT-016, SL-DCT-023 | API schema parity lint contract | Static lint shall compare `docs/api/endpoints.md`, `docs/schemas/api_schemas.md`, and `schemas/api/*.schema.json` so every endpoint schema reference has a documented schema file and every active API schema file is documented. | Must | V-SL-DCT-025 |
| SL-DCT-026 | L2 | SL-DCT-002, SL-DCT-005, SL-DCT-006, SL-DCT-023 | Event schema parity lint contract | Static lint shall compare `docs/schemas/events.md` and `schemas/events/*.schema.json` so every event inventory row has a schema file, every event schema file is inventoried, and each schema `event_type` constant matches the inventory. | Must | V-SL-DCT-026 |
| SL-DCT-027 | L2 | SL-DECOMP-005, SL-REQ-QUAL-008 | Environment variable parity lint contract | Static lint shall compare `.env.example` and `docs/operations/environment_variables.md` so every documented `STREAM_LITE_*` variable appears in both files with canonical names before implementation begins. | Must | V-SL-DCT-027 |
| SL-DCT-028 | L2 | SL-DECOMP-006, SL-OBS-025 | Metrics catalog parity lint contract | Static lint shall compare metric references across docs with `docs/operations/prometheus_metrics.md` and fail on undocumented metrics or duration metric names that do not use `_duration_seconds`. | Must | V-SL-DCT-028 |
| SL-DCT-029 | L2 | SL-DCT-007, SL-DCT-022, SL-DCT-023 | Enum invalid fixture contract | Each active API, event, and artifact schema that constrains enum or pattern-coded status/error fields shall have at least one invalid fixture that proves unsupported enum or code values are rejected by executable schema validation. | Must | V-SL-DCT-029 |
| SL-DCT-030 | L2 | SL-DCT-009, SL-DCT-022, SL-DCT-023 | Timestamp invalid fixture contract | Each active API, event, and artifact schema containing serialized timestamps shall have at least one invalid fixture that proves non-RFC3339 or non-UTC timestamp values are rejected by executable schema validation. | Must | V-SL-DCT-030 |
| SL-DCT-031 | L2 | SL-DCT-010, SL-DCT-022, SL-DCT-023 | Path-safety invalid fixture contract | Each active API, event, and artifact schema containing operator-visible paths or locators shall have at least one invalid fixture that proves unsafe host paths, traversal paths, or disallowed locator forms are rejected by executable schema validation. | Must | V-SL-DCT-031 |
| SL-DCT-032 | L2 | SL-DCT-011, SL-DCT-012, SL-DCT-014, SL-DCT-024 | Artifact schema parity lint contract | Static lint shall compare `docs/schemas/artifact_schemas.md`, `schemas/artifacts/*.schema.json`, and `schemas/examples/artifacts/*.json` so every artifact inventory row has a schema file, every artifact schema file is inventoried, and every artifact schema has valid and invalid examples. | Must | V-SL-DCT-032 |
| SL-DCT-033 | L2 | SL-DCT-022, SL-DCT-029, SL-DCT-030, SL-DCT-031 | Deep invalid fixture lint contract | Static lint shall fail before implementation if active schema families are missing required enum-invalid, timestamp-invalid, or path-invalid example coverage defined by the high-risk fixture contracts. | Must | V-SL-DCT-033 |

## Acceptance Criteria

The requirement is accepted when the repository contains a complete active contract inventory, schema validation fixtures pass for API responses and events, output/quarantine/presentation/evidence schemas are documented, and the verification matrix maps each schema to at least one validation method.

## 2026-04-25 Owning Contract Artifacts

The following active v0.1 contract artifacts decompose this requirement for implementation planning:

| Contract area | Artifact path | Implementation meaning |
|---|---|---|
| API routes | `docs/api/endpoints.md` | FastAPI route implementation shall match route, schema, status, idempotency, timeout, log, and metric entries. |
| API errors | `docs/api/errors.md` | API and dashboard shall use the listed stable error codes and operator-safe message rules. |
| API schema inventory | `docs/schemas/api_schemas.md`, `stream_lite/schemas/api/*.schema.json` | Pydantic models and OpenAPI output shall remain compatible with the documented schema names. |
| Event schema inventory | `docs/schemas/events.md`, `stream_lite/schemas/events/*.schema.json` | Producers and consumers shall validate active event envelope fields and event type constants. |
| Artifact schemas | `stream_lite/schemas/artifacts/*.schema.json` | Processing summaries, output manifests, and quarantine records shall validate against these schema stubs. |
| Logical data model | `docs/data/logical_model.md` | Migration design shall preserve table ownership, required relationships, and transaction boundaries. |
