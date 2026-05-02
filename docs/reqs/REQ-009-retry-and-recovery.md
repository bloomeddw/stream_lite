# REQ-009: Retry and Recovery Requirements

## Capability Intent

The system shall recover from retryable validation, processing, delivery, broker, and service failures without losing job metadata or creating duplicate outputs.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-RET-001 | Retry policy shall be configured through the retry environment variables listed in this document and applied per stage: validation, processing, and delivery. | Must | V-SL-RET-001 |
| SL-RET-002 | Default processing retry count shall be 3 attempts. | Must | V-SL-RET-002 |
| SL-RET-003 | Default delivery retry count shall be 3 attempts. | Must | V-SL-RET-003 |
| SL-RET-004 | Retry delay shall use exponential backoff with initial delay, multiplier, maximum delay, and jitter flag from `STREAM_LITE_RETRY_INITIAL_BACKOFF_SECONDS`, `STREAM_LITE_RETRY_BACKOFF_MULTIPLIER`, `STREAM_LITE_RETRY_MAX_BACKOFF_SECONDS`, and `STREAM_LITE_RETRY_JITTER_ENABLED`. | Must | V-SL-RET-004 |
| SL-RET-005 | Default retry policy for local demo profiles shall be 3 attempts, 1 second initial delay, multiplier `2.0`, maximum delay 30 seconds, and jitter enabled for asynchronous event retries. | Must | V-SL-RET-005 |
| SL-RET-006 | A job entering retry shall transition to `RETRY_PENDING` and record next retry time. | Must | V-SL-RET-006 |
| SL-RET-007 | Retry attempts shall preserve original job ID. | Must | V-SL-RET-007 |
| SL-RET-008 | Retry attempts shall increment attempt number monotonically by stage. | Must | V-SL-RET-008 |
| SL-RET-009 | Exhausted retries shall transition the job to `FAILED`. | Must | V-SL-RET-009 |
| SL-RET-010 | Non-retryable failures shall transition directly to `FAILED` or `QUARANTINED` based on stage. | Must | V-SL-RET-010 |
| SL-RET-011 | Service restart shall not reset retry counters. | Must | V-SL-RET-011 |
| SL-RET-012 | The system shall support manual retry of eligible failed jobs through `POST /jobs/{job_id}/retry` and the dashboard; manual retry shall create a new stage attempt, preserve the original `job_id`, and require an operator-visible reason. | Must | V-SL-RET-012 |

## Retry Configuration Surface

| Setting | Env var | Default | Allowed values |
|---|---|---:|---|
| Max attempts | `STREAM_LITE_RETRY_MAX_ATTEMPTS` | `3` | integer `0` through `10` |
| Initial backoff | `STREAM_LITE_RETRY_INITIAL_BACKOFF_SECONDS` | `1` | integer `1` through `3600` |
| Multiplier | `STREAM_LITE_RETRY_BACKOFF_MULTIPLIER` | `2.0` | number `1.0` through `10.0` |
| Max backoff | `STREAM_LITE_RETRY_MAX_BACKOFF_SECONDS` | `30` | integer `1` through `86400` |
| Jitter | `STREAM_LITE_RETRY_JITTER_ENABLED` | `true` | `true` or `false` |

Retry attempt count includes the initial attempt. With default `3`, the system performs one initial attempt and up to two retry attempts for the same stage.

## Retryable Failure Codes

| Code | Retryable | Stage |
|---|---:|---|
| `BROKER_UNAVAILABLE` | yes | event publication/consumption |
| `PROCESSOR_TIMEOUT` | yes | processing |
| `PROCESSOR_TRANSIENT_ERROR` | yes | processing |
| `DESTINATION_TEMPORARILY_UNAVAILABLE` | yes | delivery |
| `FILE_NOT_READABLE` | no by default | validation |
| `SCHEMA_INVALID` | no | validation |
| `PATH_POLICY_VIOLATION` | no | validation/delivery |
| `EXTENSION_NOT_ALLOWED` | no | validation |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-RET-NFR-001 | Retry counter persistence across restart | 100% |
| SL-RET-NFR-002 | Duplicate output creation after retry | 0 duplicates in fixture tests |
| SL-RET-NFR-003 | Exhausted retry terminal-state correctness | 100% |
| SL-RET-NFR-004 | Manual retry API p95 latency for accepted retry request | <= 300 ms |
| SL-RET-NFR-005 | Recovery of pending retry jobs after service restart | <= 10 seconds after service readiness |

## Acceptance Criteria

The requirement is accepted when simulated transient failures retry according to policy, exhausted failures become terminal, retry state survives restart, and manual retry can move an eligible failed job back into the processing or delivery flow.

## Manual Retry Eligibility Contract

| Job condition | Manual retry result | API status/error |
|---|---|---|
| Job state is `FAILED` and latest failed stage is `PROCESSING` with retryable code `PROCESSOR_TIMEOUT` or `PROCESSOR_TRANSIENT_ERROR` | Accepted; creates a new processing attempt under the same `job_id`. | `202` command result |
| Job state is `FAILED` and latest failed stage is `DELIVERING` with retryable code `DESTINATION_TEMPORARILY_UNAVAILABLE` | Accepted; creates a new delivery attempt under the same `job_id`. | `202` command result |
| Job state is `FAILED` and operator supplies a non-empty reason for processing or delivery retry where the latest code is not in the retryable catalog | Accepted only when the failed stage is processing or delivery and the API records `manual_override=true`, `operator_reason`, and `requested_at`. | `202` command result |
| Job state is `QUARANTINED` due to `EXTENSION_NOT_ALLOWED`, `SCHEMA_INVALID`, `PATH_POLICY_VIOLATION`, `FILE_TOO_LARGE`, `FILE_EMPTY` | Rejected; validation-policy failures are not manually retryable in v0.1. | `409 JOB_NOT_RETRYABLE` |
| Job state is `COMPLETED`, `VALIDATING`, `PROCESSING`, `DELIVERING`, or `RETRY_PENDING` | Rejected; only eligible `FAILED` jobs may be manually retried in v0.1. | `409 JOB_NOT_RETRYABLE` |

## Applied Decision Records

| Decision | Requirement impact |
|---|---|
| DEC-006 manual retry eligibility | Manual retry is allowed for eligible failed processing/delivery jobs and blocked for validation-policy quarantine failures. |

## L2 Contract Decomposition Requirements

These rows decompose retry behavior into classification, backoff, execution, exhaustion, and manual retry contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-RET-016 | L2 | SL-RET-001, SL-RET-002, SL-RET-003 | Retry classification contract | Each failure shall be classified with failure class, error code, retryable flag, owning stage, operator-safe message, and required terminal state when retry is not allowed. | Must | V-SL-RET-016 |
| SL-RET-017 | L2 | SL-RET-004, SL-RET-005, SL-RET-006 | Retry backoff contract | Automatic retry delay shall use configured attempts, initial backoff, multiplier, max backoff, and jitter, and persist `next_retry_at` before entering `RETRY_PENDING`. | Must | V-SL-RET-017 |
| SL-RET-018 | L2 | SL-RET-007, SL-RET-008, SL-RET-013 | Retry execution contract | Due retries shall re-enter only the failed eligible stage, create/increment the stage attempt, preserve prior history, and emit retry execution logs and metrics. | Must | V-SL-RET-018 |
| SL-RET-019 | L2 | SL-RET-009, SL-RET-010, SL-RET-014 | Retry exhaustion contract | Exhausted retry handling shall persist final failed attempt, append `FAILED` state, enqueue dead-letter/failure event, expose failure detail, and prevent further automatic retries. | Must | V-SL-RET-019 |
| SL-RET-020 | L2 | SL-RET-011, SL-RET-012, SL-RET-015 | Manual retry contract | Manual retry shall require an eligible job, persist a control command with idempotency key and operator reason, reset only the eligible stage, and reject ineligible jobs with `409 MANUAL_RETRY_NOT_ALLOWED`. | Must | V-SL-RET-020 |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-RET-013 | L3 | SL-RET-004, SL-RET-005, SL-RET-006 | `stream_lite.retry.scheduler.schedule_retry` | The retry scheduling surface shall compute due time using configured initial delay, multiplier, max delay, jitter setting, attempt number, and failure class, then persist `RETRY_PENDING` without resetting job identity. | V-SL-RET-013 |
| SL-RET-014 | L3 | SL-RET-009, SL-RET-010 | `stream_lite.retry.scheduler.finalize_exhausted_retry` | The retry exhaustion surface shall transition the job to `FAILED`, persist the final failure details, and enqueue `job.failed` when the maximum retry count is exceeded or the failure is non-retryable. | V-SL-RET-014 |
| SL-RET-015 | L3 | SL-RET-012 | `stream_lite.retry.manual.accept_manual_retry_command` | The manual retry command surface shall verify eligibility, require an operator-visible reason, persist the command and idempotency key, and create the next stage attempt only after validation succeeds. | V-SL-RET-015 |
