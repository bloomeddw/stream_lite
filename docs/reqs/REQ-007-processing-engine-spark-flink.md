# REQ-007: Processing Engine Requirements for Spark MVP and Future Flink Profile

## Capability Intent

The system shall process validated files through Apache Spark in the v0.1 MVP profile. The processing contract shall remain engine-neutral enough to permit a future Apache Flink adapter, but v0.1 implementation and verification shall not attempt to start or test Flink.

## Engine Positioning

Spark is the required v0.1 processing engine because the demo is file-drop oriented and batch-like. Flink is future-compatible scope only and shall require a later decision record plus updated verification evidence before becoming an accepted runtime profile.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-PRO-001 | The processing service shall consume jobs in `VALIDATED` state. | Must | V-SL-PRO-001 |
| SL-PRO-002 | The processing service shall transition a job to `PROCESSING` before invoking Spark or Flink work. | Must | V-SL-PRO-002 |
| SL-PRO-003 | The processing engine shall read the source file from the registered stable file locator. | Must | V-SL-PRO-003 |
| SL-PRO-004 | The default v0.1 transformation shall read the validated input file and write a job-scoped processed output artifact plus `processing_summary.json`; for `.csv` it shall preserve rows and add processing metadata, for `.json` it shall write normalized pretty-printed JSON, and for `.txt` it shall copy text content with metadata sidecar only. | Must | V-SL-PRO-004 |
| SL-PRO-005 | The processing summary shall include job ID, engine name, `engine_version` set to the detected version string or `unknown`, input locator, output locator, `row_count` set to an integer or `null` for non-tabular files, byte count, start time, end time, duration, and status. | Must | V-SL-PRO-005 |
| SL-PRO-006 | Successful processing shall transition jobs to `PROCESSED`. | Must | V-SL-PRO-006 |
| SL-PRO-007 | Retryable processing failures shall transition jobs to `RETRY_PENDING` when retry attempts remain. | Must | V-SL-PRO-007 |
| SL-PRO-008 | Non-retryable or exhausted processing failures shall transition jobs to `FAILED`. | Must | V-SL-PRO-008 |
| SL-PRO-009 | The Spark engine adapter shall expose the documented job input and output contract; future Flink adapters shall use the same contract before activation. | Must | V-SL-PRO-009 |
| SL-PRO-010 | The system shall support `.csv`, `.json`, and `.txt` fixture processing in the default demo profile; unsupported extensions shall be rejected during validation rather than reaching processing. | Must | V-SL-PRO-010 |
| SL-PRO-011 | The processing service shall write outputs to a job-scoped staging location before delivery begins. | Must | V-SL-PRO-011 |
| SL-PRO-012 | The processing service shall not mark a job `PROCESSED` until the output artifact and processing summary are both durable. | Must | V-SL-PRO-012 |

## Processing Contract

Input:

```json
{
  "job_id": "uuid",
  "watcher_id": "uuid",
  "input_locator": "path-or-uri",
  "file_name": "string",
  "extension": "string",
  "content_hash": "sha256",
  "processing_profile": "default|csv_summary|json_normalize|text_copy"
}
```

Output:

```json
{
  "job_id": "uuid",
  "engine": "spark|flink",
  "status": "processed|failed",
  "output_locator": "path-or-uri|null",
  "summary_locator": "path-or-uri|null",
  "records_read": "integer|null",
  "records_written": "integer|null",
  "bytes_read": "integer",
  "bytes_written": "integer|null",
  "error_code": "string|null"
}
```

## Default Processing Output Contract

| Input type | Output artifact | Required summary fields |
|---|---|---|
| `.csv` | UTF-8 CSV written to staging with original rows preserved and optional metadata columns only if documented in `processing_summary.json`. | `job_id`, `input_rows`, `output_rows`, `source_sha256`, `processor_version`, `engine`, `started_at`, `completed_at`, `duration_seconds`, `status` |
| `.json` | UTF-8 JSON written to staging as object or array matching the parsed input shape. | Same as `.csv`; row counts may be `null` and `record_count` shall be used when top-level array is present. |
| `.txt` | UTF-8 text copied to staging without content transformation. | Same as `.csv`; row counts may be line counts. |

## Worker Claiming Contract

A worker shall claim work with a single database transaction that changes state from `VALIDATED` or eligible `RETRY_PENDING` to `PROCESSING`. If no row is changed, the worker shall not process the file and shall log `JOB_CLAIM_CONFLICT` at `info` level.

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-PRO-NFR-001 | Processing startup overhead for warm engine profile | <= 10 seconds p95 |
| SL-PRO-NFR-002 | Processing success rate for valid fixture set | >= 99% |
| SL-PRO-NFR-003 | Processing summary creation | 100% of processing attempts |
| SL-PRO-NFR-004 | Output durability before `PROCESSED` state | 100% |
| SL-PRO-NFR-005 | End-to-end throughput for files <= 1 MB | >= 100 files/minute local demo |
| SL-PRO-NFR-006 | Engine adapter contract compatibility | 100% shared contract test pass for selected engine |

## Acceptance Criteria

The requirement is accepted when the Spark default engine processes valid CSV, JSON, and text fixtures, writes job-scoped outputs and summaries, records attempts, and drives correct state transitions without requiring dashboard-specific logic. Flink-specific tests are not required for v0.1 acceptance.

## Migrated Processing Orchestration Requirements

The following orchestration requirements were migrated from the duplicate draft `REQ-006-processing-orchestration.md` and normalized under the active processing requirement namespace.

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-PRO-013 | Processing workers shall consume processable file events from the configured event bus. | Must | V-SL-PRO-013 |
| SL-PRO-014 | Processing workers shall claim jobs using a PostgreSQL-backed lock or atomic state transition that prevents two workers from processing the same job concurrently. | Must | V-SL-PRO-014 |
| SL-PRO-015 | Processing workers shall verify that validation completed successfully before invoking Spark or Flink work. | Must | V-SL-PRO-015 |
| SL-PRO-016 | The default demo processing action shall produce an output artifact and a durable output manifest. | Must | V-SL-PRO-016 |
| SL-PRO-017 | Processing shall preserve the original file checksum in job metadata and the output manifest. | Must | V-SL-PRO-017 |
| SL-PRO-018 | Processing worker concurrency shall be configured by `STREAM_LITE_WORKER_CONCURRENCY`, with allowed integer values `1` through `8` and default `2` concurrent jobs per worker container for the local demo profile. | Must | V-SL-PRO-018 |
| SL-PRO-019 | Worker shutdown shall stop accepting new jobs and allow in-flight jobs up to 30 seconds to finish before marking unfinished work recoverable. | Must | V-SL-PRO-019 |
| SL-PRO-020 | Processing failures shall persist error details and publish the configured job failure event. | Must | V-SL-PRO-020 |

## Migrated Processing Data Requirements

| ID | Requirement | Verification |
|---|---|---|
| SL-PRO-DATA-001 | Output manifests shall include `job_id`, `source_sha256`, `processor_version`, `started_at`, `completed_at`, `duration_seconds`, and produced output paths. | V-SL-PRO-DATA-001 |
| SL-PRO-DATA-002 | Worker or stage ownership records shall include `worker_id`, `container_id` when available, service name, stage, attempt number, lease expiration timestamp, and heartbeat timestamp for each claimed job stage. | V-SL-PRO-DATA-002 |

## Migrated Processing Verification Requirements

| ID | Verification Method | Evidence Artifact |
|---|---|---|
| V-SL-PRO-013 | Event consumption integration test. | Published event list and consumed job list. |
| V-SL-PRO-014 | Concurrent worker claim test with at least 5 workers. | Job claim audit proving zero duplicate claims. |
| V-SL-PRO-015 | Validation-before-processing state transition test. | Job state history showing validation before processing. |
| V-SL-PRO-016 | Default processing fixture test. | Output artifact and manifest. |
| V-SL-PRO-017 | Manifest checksum validation. | Source checksum comparison evidence. |
| V-SL-PRO-018 | Worker concurrency configuration test. | Worker startup config and observed concurrency evidence. |
| V-SL-PRO-019 | Graceful shutdown test. | Worker logs and recovery state report. |
| V-SL-PRO-020 | Injected processing failure test. | Failed job record and failure event evidence. |
| V-SL-PRO-DATA-001 | Manifest schema validation. | Manifest validation report. |
| V-SL-PRO-DATA-002 | Worker registry data check. | Stage ownership claim query result showing worker ID, stage, attempt number, lease expiration, and heartbeat. |

## Applied Decision Records

| Decision | Requirement impact |
|---|---|
| DEC-004 processing engine | Active v0.1 processing implementation and verification target Spark only; Flink is deferred. |

## L2 Contract Decomposition Requirements

These rows decompose processing into engine selection, claim, input, output, completion, and failure contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-PRO-024 | L2 | SL-PRO-001, SL-PRO-002 | Processing engine selection contract | Processing shall accept only `spark` in active v0.1 scope, record the selected engine on processing attempts, and fail startup for unsupported active values before claiming jobs. | Must | V-SL-PRO-024 |
| SL-PRO-025 | L2 | SL-PRO-003, SL-PRO-004, SL-JOB-014, SL-JOB-015 | Processing claim contract | Before reading input or writing output, the processor shall claim the processing stage, verify eligible state, set lease expiration, and emit no side effects when the claim fails. | Must | V-SL-PRO-025 |
| SL-PRO-026 | L2 | SL-PRO-005, SL-PRO-006, SL-PRO-DATA-001 | Processing input contract | Processing input resolution shall use persisted file identity and validation result, verify readability, and reject jobs missing successful validation. | Must | V-SL-PRO-026 |
| SL-PRO-027 | L2 | SL-PRO-007, SL-PRO-008, SL-PRO-022 | Demo transform output contract | The MVP Spark transform shall create a deterministic output artifact containing source metadata, processing timestamp, summary fields, and checksum recorded with the processing attempt. | Must | V-SL-PRO-027 |
| SL-PRO-028 | L2 | SL-PRO-009, SL-PRO-010, SL-PRO-011, SL-PRO-012, SL-PRO-023 | Processing completion contract | Processing completion shall persist attempt result and output locator before transitioning to `PROCESSED`, enqueueing downstream events, or making delivery work visible. | Must | V-SL-PRO-028 |
| SL-PRO-029 | L2 | SL-PRO-013, SL-PRO-014, SL-PRO-015 | Processing failure contract | Processing failures shall classify retryability, persist failed attempts, release/expire claims, schedule retry when eligible, and transition to `FAILED` only when policy requires. | Must | V-SL-PRO-029 |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-PRO-021 | L3 | SL-PRO-014, SL-PRO-015 | `stream_lite.processing.worker.claim_processable_job` | The processing claim surface shall atomically claim one validated job, reject jobs that are not validated, and prevent concurrent processing by multiple workers. | V-SL-PRO-021 |
| SL-PRO-022 | L3 | SL-PRO-016, SL-PRO-DATA-001 | `stream_lite.processing.spark.run_demo_transform` | The Spark processing surface shall produce the demo output artifact and `processing_summary.json` with duration seconds and manifest-compatible locators. | V-SL-PRO-022 |
| SL-PRO-023 | L3 | SL-PRO-020 | `stream_lite.processing.worker.complete_processing_attempt` | The processing completion surface shall persist attempt status, transition job state, and enqueue `processing.completed` or `processing.failed` with the attempt number. | V-SL-PRO-023 |
