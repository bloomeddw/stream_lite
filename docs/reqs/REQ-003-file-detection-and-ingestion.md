# REQ-003: File Detection and Ingestion Requirements

## Capability Intent

The system shall detect files arriving in watched source folders, wait until files are stable, register ingestion jobs, publish file-detected events, and prevent duplicate processing for identical file arrivals. The watcher shall stay healthy and idle when no eligible files are available.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-FDI-001 | The watcher service shall detect newly created files in active source folders. | Must | V-SL-FDI-001 |
| SL-FDI-002 | The watcher service shall ignore directories unless recursive watch mode is enabled. | Must | V-SL-FDI-002 |
| SL-FDI-003 | Recursive watch mode shall be set by watcher schema field `recursive`, default `false`; v0.1 shall accept the field and shall reject `true` with `422 RECURSIVE_WATCH_DEFERRED` until recursive implementation is verified. | Should | V-SL-FDI-003 |
| SL-FDI-004 | A detected file shall enter `STABILIZING` before validation begins. | Must | V-SL-FDI-004 |
| SL-FDI-005 | A file shall be considered stable when its byte size is unchanged across at least two checks over at least 1 second. | Must | V-SL-FDI-005 |
| SL-FDI-006 | The system shall calculate a content hash for each stable file before registering it as a job. | Must | V-SL-FDI-006 |
| SL-FDI-007 | The system shall create exactly one job for the same watcher ID, source path, byte size, and content hash unless a future requirements-backed reprocess endpoint creates a new reprocess attempt. | Must | V-SL-FDI-007 |
| SL-FDI-008 | The system shall publish a `file.detected` event only after a job ID has been allocated and a `DETECTED` job record has committed. | Must | V-SL-FDI-008 |
| SL-FDI-009 | The system shall publish a `file.stable` event after stability checks pass. | Must | V-SL-FDI-009 |
| SL-FDI-010 | The system shall publish a `job.registered` event after stable-file metadata, deduplication result, watcher ID, source folder ID, and current state `REGISTERED` have committed. | Must | V-SL-FDI-010 |
| SL-FDI-011 | The watcher service shall not delete or modify source files during detection. | Must | V-SL-FDI-011 |
| SL-FDI-012 | The system shall record source file path, file name, extension, byte size, modified timestamp, hash, watcher ID, source folder ID, and detection timestamp. | Must | V-SL-FDI-012 |
| SL-FDI-013 | The watcher service shall continue polling or subscribing to folder changes while no files are present without creating jobs or emitting failure events. | Must | V-SL-FDI-013 |
| SL-FDI-014 | The watcher service shall record an `idle` observation when an active watcher has no eligible files in any configured source folder for at least one dashboard refresh interval. | Should | V-SL-FDI-014 |
| SL-FDI-015 | The watcher service shall create the initial job record in state `DETECTED` before emitting the first job-scoped event for a file. | Must | V-SL-FDI-015 |
| SL-FDI-016 | File deduplication shall run before creating a new `DETECTED` job; when a duplicate deduplication key already exists, the watcher shall not create a new job and shall record a duplicate-suppression observation linked to the existing job ID. | Must | V-SL-FDI-016 |
| SL-FDI-017 | A duplicate-suppression observation shall include watcher ID, source folder ID, source display path, byte size, content hash, existing job ID, observed timestamp, and reason code `DUPLICATE_SUPPRESSED`. | Must | V-SL-FDI-017 |
| SL-FDI-018 | The watcher shall not emit `file.detected`, `file.stable`, or `job.registered` for a duplicate-suppressed file because no new job lifecycle is created. | Must | V-SL-FDI-018 |
| SL-FDI-019 | The watcher shall associate each job with exactly one configured source folder ID so route resolution can use the source folder route tags during delivery. | Must | V-SL-FDI-019 |
| SL-FDI-020 | If the watcher cannot persist the initial `DETECTED` job record, it shall not emit file events for that file and shall log `JOB_REGISTRATION_FAILED` with the source display path and correlation ID. | Must | V-SL-FDI-020 |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-FDI-NFR-001 | File detection latency p95 after file appears | <= 2 seconds |
| SL-FDI-NFR-002 | Stability confirmation latency after final write | <= 3 seconds |
| SL-FDI-NFR-003 | Duplicate suppression for identical fixture files | 100% |
| SL-FDI-NFR-004 | Missed-file rate in 1,000-file local fixture run | 0 |
| SL-FDI-NFR-005 | Detection throughput for files <= 1 MB | >= 100 files/minute |
| SL-FDI-NFR-006 | Content hash algorithm | SHA-256 or stronger |
| SL-FDI-NFR-007 | False job creation while source folders are empty during a 10-minute idle test | 0 jobs |

## Acceptance Criteria

The requirement is accepted when a 10-minute empty-folder run creates zero jobs and reports idle status, and a fixture run that drops at least 1,000 small files into watched folders produces exactly one registered job per unique file, records duplicate-suppression observations without creating duplicate jobs, and emits the required events in the correct order.

## L2 Contract Decomposition Requirements

These rows decompose file detection into scan eligibility, stability, identity, deduplication, and registration contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-FDI-025 | L2 | SL-FDI-001, SL-FDI-002, SL-FDI-003, SL-FDI-004 | Source scan eligibility contract | Source scans shall consider only active watcher sources with green reachability, valid routing, and readable directories; ineligible sources shall not create file identity records. | Must | V-SL-FDI-025 |
| SL-FDI-026 | L2 | SL-FDI-005, SL-FDI-006, SL-FDI-007 | File stability contract | A file shall be stable only after size and modification time remain unchanged for the configured window, the file remains readable, and its locator resolves inside the source allowlist. | Must | V-SL-FDI-026 |
| SL-FDI-027 | L2 | SL-FDI-008, SL-FDI-009, SL-FDI-010 | File identity contract | File identity shall include source folder ID, sanitized display path, container locator, file name, extension, byte size, content hash, detected timestamp, stable timestamp, and route preview timestamp. | Must | V-SL-FDI-027 |
| SL-FDI-028 | L2 | SL-FDI-011, SL-FDI-012, SL-FDI-013 | Duplicate suppression contract | Duplicate detection shall compare the configured duplicate key before job creation, persist duplicate observations, leave the original job unchanged, and not enqueue processing or delivery for duplicates. | Must | V-SL-FDI-028 |
| SL-FDI-029 | L2 | SL-FDI-014, SL-FDI-015, SL-FDI-024 | Job registration handoff contract | Job registration shall persist the job and initial state history before emitting registration events; if persistence fails, no event shall be emitted. | Must | V-SL-FDI-029 |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-FDI-021 | L3 | SL-FDI-004, SL-FDI-015 | `stream_lite.watchers.detector.scan_source_folder` | The source scan surface shall enumerate allowlisted source folders, produce sanitized candidate file records, and never emit jobs or events directly. | V-SL-FDI-021 |
| SL-FDI-022 | L3 | SL-FDI-005, SL-FDI-020 | `stream_lite.watchers.stability.wait_for_stable_file` | The file stability surface shall compare file size and modification timestamp across the configured stability interval and return a retryable observation when the file is still changing. | V-SL-FDI-022 |
| SL-FDI-023 | L3 | SL-FDI-016, SL-FDI-018 | `stream_lite.watchers.deduplication.compute_deduplication_key` | The deduplication surface shall derive one stable key from watcher ID, source folder ID, source display path, size, and SHA-256 when available; duplicate keys shall suppress new job creation and event emission. | V-SL-FDI-023 |
| SL-FDI-024 | L3 | SL-FDI-015, SL-LIFE-002, SL-LIFE-003 | `stream_lite.watchers.registration.register_detected_file` | The job registration surface shall persist the initial job and file metadata before enqueueing outbox events for `file.detected`, `file.stable`, and `job.registered`. | V-SL-FDI-024 |
