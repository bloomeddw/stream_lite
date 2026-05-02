# Retry Policy

Default retry behavior is 3 attempts, 1 second initial backoff, x2 multiplier, 30 second max backoff, and jitter enabled for async/event retries. Validation policy failures are not retryable.

| Failure class | Detection point | Retryable | Max attempts | Backoff | Final state | Operator message | Log event | Metric | Recovery |
|---|---|---:|---:|---|---|---|---|---|---|
| `BROKER_PUBLISH_FAILURE` | outbox dispatcher publish | yes | unlimited until service shutdown unless future retention policy defines cap | reconciliation interval plus broker client retry | outbox remains pending | Broker unavailable; event will retry. | `event.publish_failed` | `stream_lite_event_publish_total{status="failed"}` | Dispatcher republishes pending outbox rows. |
| `PROCESSING_TRANSIENT_FAILURE` | Spark job execution | yes | env `STREAM_LITE_RETRY_MAX_ATTEMPTS` | env backoff with jitter | `FAILED` after exhaustion | Processing failed and retry is scheduled or exhausted. | `processing.failed` | `stream_lite_retry_scheduled_total` | Retry scheduler returns job to `PROCESSING`. |
| `DELIVERY_TRANSIENT_FAILURE` | copy/finalize to destination | yes | env `STREAM_LITE_RETRY_MAX_ATTEMPTS` | env backoff with jitter | `FAILED` or `COMPLETED_WITH_DELIVERY_ERRORS` | Delivery failed for one or more destinations. | `delivery.failed` | `stream_lite_delivery_attempt_total{status="failed"}` | Retry failed destination attempts only. |
| `DESTINATION_UNAVAILABLE` | delivery preflight/write | yes | env `STREAM_LITE_RETRY_MAX_ATTEMPTS` | env backoff with jitter | `FAILED` or `COMPLETED_WITH_DELIVERY_ERRORS` | Destination unavailable; check folder health. | `delivery.destination_unavailable` | `stream_lite_folder_health_status` | Operator restores destination; retry resumes. |
| `VALIDATION_POLICY_FAILURE` | validator | no | 0 | none | `QUARANTINED` | File violates validation policy and cannot be retried. | `validation.failed` | `stream_lite_validation_failure_total` | Future reprocess workflow required. |
| `PATH_SECURITY_FAILURE` | API/path validation/watcher | no | 0 | none | request rejected or watcher blocked | Path rejected by allowlist or traversal rule. | `security.path_rejected` | `stream_lite_error_total` | Operator chooses allowed path. |
| `COMMAND_STATE_CONFLICT` | API command handling | no | 0 | none | command `failed` | Command cannot run from current state. | `command.failed` | `stream_lite_api_command_total{status="failed"}` | Operator refreshes state and chooses valid action. |

## Retry State Rules

- Retry shall not allocate a new `job_id`.
- Retry shall create a new attempt row for the failed stage.
- Retry shall preserve prior attempt evidence.
- Manual retry shall use the same eligibility rules as automatic retry and shall return `409 JOB_NOT_RETRYABLE` when blocked.
