# Quarantine Policy

Invalid files are copied to quarantine. Source files shall never be modified, moved, or deleted by quarantine behavior.

## Quarantine Triggers

| Reason code | Trigger | Retryable | Quarantine copy required | Terminal state | Requirements |
|---|---|---:|---:|---|---|
| `EXTENSION_NOT_ALLOWED` | Extension outside the WP-07 MVP allowlist. | no | yes | `QUARANTINED` | SL-VAL-005 |
| `FILE_TOO_LARGE` | File exceeds `STREAM_LITE_MAX_FILE_SIZE_MB`. | no | yes | `QUARANTINED` | SL-VAL-004 |
| `FILE_EMPTY` | File size is zero when zero-byte files are disallowed. | no | yes | `QUARANTINED` | SL-VAL-006 |
| `SCHEMA_INVALID` | Supported CSV, JSON, or TXT content fails the WP-07 structured-format rules. | no | yes | `QUARANTINED` | SL-VAL-010 |
| `FILE_NOT_FOUND` | Stable locator no longer exists when validation starts. | no | yes when still readable source content is available; otherwise artifact-only record | `QUARANTINED` | SL-VAL-009 |
| `FILE_NOT_READABLE` | File exists but cannot be read by the validation service. | no | yes when the copy can still be attempted; otherwise artifact-only record | `QUARANTINED` | SL-VAL-009 |
| `PATH_SECURITY_FAILURE` | Path traversal or allowlist failure. | no | no for untrusted path outside allowlist | request rejected or watcher blocked | SL-SEC-001 |

## Quarantine Record Fields

`quarantine_record.json` shall include `schema_version`, `job_id`, `watcher_id`, `source_display_path`, `source_sha256`, `reason_code`, `operator_message`, `quarantine_locator`, `quarantine_display_path`, `copy_status`, `created_at`, and `correlation_id`.

## Copy Layout

Quarantine copies shall be placed under:

```text
{STREAM_LITE_QUARANTINE_ROOT}/watcher_id={watcher_id}/date=YYYY-MM-DD/job_id={job_id}/{original_filename}
{STREAM_LITE_QUARANTINE_ROOT}/watcher_id={watcher_id}/date=YYYY-MM-DD/job_id={job_id}/quarantine_record.json
```
