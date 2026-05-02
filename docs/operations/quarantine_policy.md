# Quarantine Policy

Invalid files are copied to quarantine. Source files shall never be modified, moved, or deleted by quarantine behavior.

## Quarantine Triggers

| Reason code | Trigger | Retryable | Quarantine copy required | Terminal state | Requirements |
|---|---|---:|---:|---|---|
| `UNSUPPORTED_EXTENSION` | Extension outside allowed v0.1 set. | no | yes | `QUARANTINED` | SL-VAL-004 |
| `FILE_TOO_LARGE` | File exceeds `STREAM_LITE_MAX_FILE_SIZE_MB`. | no | yes | `QUARANTINED` | SL-VAL-004 |
| `EMPTY_FILE` | File size is zero when zero-byte files are disallowed. | no | yes | `QUARANTINED` | SL-VAL-005 |
| `CSV_PARSE_ERROR` | CSV fixture cannot be parsed under v0.1 rules. | no | yes | `QUARANTINED` | SL-VAL-010 |
| `JSON_PARSE_ERROR` | JSON fixture cannot be parsed. | no | yes | `QUARANTINED` | SL-VAL-010 |
| `PATH_SECURITY_FAILURE` | Path traversal or allowlist failure. | no | no for untrusted path outside allowlist | request rejected or watcher blocked | SL-SEC-001 |

## Quarantine Record Fields

`quarantine_record.json` shall include `schema_version`, `job_id`, `watcher_id`, `source_display_path`, `source_sha256`, `reason_code`, `operator_message`, `quarantine_display_path`, `copy_status`, `created_at`, and `correlation_id`.

## Copy Layout

Quarantine copies shall be placed under:

```text
{STREAM_LITE_QUARANTINE_ROOT}/{watcher_id}/{job_id}/source/{original_filename}
{STREAM_LITE_QUARANTINE_ROOT}/{watcher_id}/{job_id}/quarantine_record.json
```
