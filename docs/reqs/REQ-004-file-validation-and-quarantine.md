# REQ-004: File Validation and Quarantine Requirements

## Capability Intent

The system shall validate incoming files before processing, classify invalid files with deterministic reason codes, and quarantine invalid files by copying them to a quarantine root while preserving the original source file unchanged.

## Supported Validation Dimensions

- File existence and readability.
- File size limits.
- File extension allowlist.
- MIME/type detection when available.
- Empty file detection.
- Duplicate detection during watcher registration before validation.
- Basic schema validation for supported structured files.
- Operator-configured validation rules.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-VAL-001 | The validation service shall consume `job.registered` events and shall run a reconciliation query at least every 10 seconds for `REGISTERED` jobs that have no validation attempt record. | Must | V-SL-VAL-001 |
| SL-VAL-002 | The validation service shall transition jobs from `REGISTERED` to `VALIDATING`. | Must | V-SL-VAL-002 |
| SL-VAL-003 | The validation service shall reject files larger than the configured maximum file size. | Must | V-SL-VAL-003 |
| SL-VAL-004 | The default maximum file size shall be 100 MB for local demo profiles and shall be configured by `STREAM_LITE_MAX_FILE_SIZE_MB`; values below 1 MB or above 10,240 MB shall be rejected at startup for the local demo profile. | Must | V-SL-VAL-004 |
| SL-VAL-005 | The validation service shall reject file extensions not present in the watcher allowlist. | Must | V-SL-VAL-005 |
| SL-VAL-006 | The validation service shall reject empty files. | Must | V-SL-VAL-006 |
| SL-VAL-007 | Valid files shall transition to `VALIDATED`. | Must | V-SL-VAL-007 |
| SL-VAL-008 | Invalid files shall transition to `INVALID` and then `QUARANTINED`. | Must | V-SL-VAL-008 |
| SL-VAL-009 | Each invalid file shall have at least one machine-readable reason code. | Must | V-SL-VAL-009 |
| SL-VAL-010 | The system shall record validation start time, end time, duration, status, rules applied, and reason codes. | Must | V-SL-VAL-010 |
| SL-VAL-011 | The system shall publish `file.validated` for valid files. | Must | V-SL-VAL-011 |
| SL-VAL-012 | The system shall publish `file.quarantined` for quarantined files. | Must | V-SL-VAL-012 |
| SL-VAL-013 | For local demo profiles, each quarantined file shall create a quarantine record and copy the original file to `<quarantine_root>/watcher_id=<watcher_id>/date=YYYY-MM-DD/job_id=<job_id>/`; the original source file shall not be deleted or modified by quarantine handling. | Must | V-SL-VAL-013 |
| SL-VAL-016 | Each quarantine record shall persist `quarantine_record_id`, `job_id`, `file_id`, sanitized source display path, quarantine locator, reason codes, copy status, created timestamp, checksum when available, and operator-safe message before `file.quarantined` is published. | Must | V-SL-VAL-016 |

## Validation Reason Codes

| Code | Trigger | Retryable | Terminal state |
|---|---|---:|---|
| `FILE_NOT_FOUND` | Stable locator no longer exists when validation starts. | no | `QUARANTINED` |
| `FILE_NOT_READABLE` | File exists but validation service cannot read it. | no | `QUARANTINED` |
| `FILE_EMPTY` | File byte size is `0`. | no | `QUARANTINED` |
| `FILE_TOO_LARGE` | File byte size exceeds `STREAM_LITE_MAX_FILE_SIZE_MB`. | no | `QUARANTINED` |
| `EXTENSION_NOT_ALLOWED` | Lowercased extension is not in watcher allowlist. | no | `QUARANTINED` |
| `SCHEMA_INVALID` | Structured file parser fails configured schema checks. | no | `QUARANTINED` |
| `DUPLICATE_SUPPRESSED` | Deduplication key already has an active or terminal job before new job creation. | no | No new job is created; duplicate observation is recorded by REQ-003. |

## Structured File MVP Contract

| File type | MVP validation behavior |
|---|---|
| `.csv` | File must parse with Python CSV reader using UTF-8, comma delimiter, and at least one row. Header validation is applied only when watcher schema fields are configured. |
| `.json` | File must parse as JSON object or JSON array using UTF-8. Schema validation is applied only when watcher JSON schema is configured. |
| `.txt` | File must be UTF-8 decodable and non-empty. |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-VAL-NFR-001 | Validation latency p95 for files <= 1 MB | <= 1 second |
| SL-VAL-NFR-002 | Validation latency p95 for files <= 100 MB | <= 5 seconds |
| SL-VAL-NFR-003 | Invalid fixture classification accuracy | 100% |
| SL-VAL-NFR-004 | Quarantine record creation for invalid files | 100% |
| SL-VAL-NFR-005 | Validation result persistence before event publication | 100% |

## Acceptance Criteria

The requirement is accepted when a validation fixture set containing valid files, empty files, oversized files, unsupported extensions, unreadable files, duplicates, and schema-invalid files produces deterministic validation outcomes, duplicate-suppression observations for duplicate arrivals, persisted reason codes, and correct terminal states.

## Applied Decision Records

| Decision | Requirement impact |
|---|---|
| DEC-005 quarantine handling | v0.1 quarantine copies invalid files to the quarantine root and never deletes or modifies the source file. |

## L2 Contract Decomposition Requirements

These rows decompose validation and quarantine into deterministic rule, outcome, quarantine-copy, and event/log contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-VAL-020 | L2 | SL-VAL-001, SL-VAL-002, SL-VAL-003, SL-VAL-004 | Validation rule contract | Validation attempts shall evaluate configured extension, size, readability, structured-file checks, and path-safety checks in deterministic order and persist rule results. | Must | V-SL-VAL-020 |
| SL-VAL-021 | L2 | SL-VAL-005, SL-VAL-006, SL-VAL-007 | Validation outcome contract | Validation outcome shall be exactly `VALIDATED`, `INVALID`, or `FAILED`; rule failures shall use `INVALID`, infrastructure failures shall use retry/failure handling, and each outcome shall map to a state transition. | Must | V-SL-VAL-021 |
| SL-VAL-022 | L2 | SL-VAL-008, SL-VAL-009, SL-VAL-010, SL-VAL-016 | Quarantine record contract | Quarantine records shall include job ID, source display path, source content hash when available, quarantine locator, reason code, validation attempt ID, copied byte size, checksum, timestamp, and operator-safe message. | Must | V-SL-VAL-022 |
| SL-VAL-023 | L2 | SL-VAL-011, SL-VAL-012, SL-VAL-013 | Quarantine filesystem contract | Quarantine shall copy rather than move files, write under the configured quarantine root, verify copied bytes/checksum when available, and leave the original source file untouched. | Must | V-SL-VAL-023 |
| SL-VAL-024 | L2 | SL-VAL-011, SL-VAL-012, SL-VAL-019 | Validation event/log contract | Validation completion shall persist the attempt, append state history, enqueue the correct validation or quarantine event, emit a structured log, and update metrics in that order. | Must | V-SL-VAL-024 |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-VAL-017 | L3 | SL-VAL-001, SL-VAL-010 | `stream_lite.validation.rules.validate_file_contract` | The validation rules surface shall return pass/fail status, rule IDs applied, duration seconds, and machine-readable reason codes without modifying the source file. | V-SL-VAL-017 |
| SL-VAL-018 | L3 | SL-VAL-013, SL-VAL-016 | `stream_lite.validation.quarantine.copy_to_quarantine` | The quarantine copy surface shall copy invalid files to the configured quarantine locator, preserve the source file, compute checksum when available, and persist the quarantine record before publishing `file.quarantined`. | V-SL-VAL-018 |
| SL-VAL-019 | L3 | SL-VAL-011, SL-VAL-012 | `stream_lite.validation.service.complete_validation_stage` | The validation stage service shall transition valid jobs to `VALIDATED`, invalid jobs to `QUARANTINED`, and write the corresponding event outbox rows with the same correlation ID. | V-SL-VAL-019 |
