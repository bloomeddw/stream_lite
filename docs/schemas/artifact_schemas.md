# Artifact Schema Contract Inventory

Artifact schemas are implementation contracts for persisted processing, delivery, and quarantine records. JSON schema files live under `stream_lite/schemas/artifacts/`. Valid and invalid example payloads live under `stream_lite/schemas/examples/artifacts/`.

## Shared Field Types

| Type | Contract |
|---|---|
| `schema_version` | Semantic version string in `major.minor.patch` form. |
| `uuid` | RFC 4122 UUID string; lowercase canonical serialization preferred. |
| `rfc3339_utc` | RFC 3339 UTC string ending in `Z`. |
| `display_path` | Sanitized operator-facing path; never host-only absolute path. |
| `locator` | Safe artifact locator; no Windows host path, traversal segment, or `file://` form. |
| `sha256` | Lowercase SHA-256 hex string. |

## Artifact Schemas

| Schema | File | Required fields | Notes | Example |
|---|---|---|---|---|
| `ProcessingSummary` | `schemas/artifacts/processing_summary.schema.json` | `schema_version`, `job_id`, `engine`, `engine_version`, `input_locator`, `output_locator`, `started_at`, `completed_at`, `duration_seconds`, `status`, `correlation_id` | `row_count`, `record_count`, and `byte_count` may be `null` when not available. | `schemas/examples/artifacts/processing_summary.valid.json` |
| `OutputManifest` | `schemas/artifacts/output_manifest.schema.json` | `schema_version`, `job_id`, `watcher_id`, `source_sha256`, `processing_summary_locator`, `destination_outcomes`, `status`, `created_at`, `correlation_id` | Destination outcomes remain schema-owned objects; runtime code shall not invent undocumented fields. | `schemas/examples/artifacts/output_manifest.valid.json` |
| `QuarantineRecord` | `schemas/artifacts/quarantine_record.schema.json` | `schema_version`, `job_id`, `watcher_id`, `source_display_path`, `source_sha256`, `reason_code`, `operator_message`, `quarantine_locator`, `quarantine_display_path`, `copy_status`, `created_at`, `correlation_id` | Operator-facing paths must stay sanitized and locators must remain container-safe. | `schemas/examples/artifacts/quarantine_record.valid.json` |

## Example Fixture Rule

Each artifact schema shall have at least one `*.valid.json` fixture under `schemas/examples/artifacts/`. Active artifact schemas shall also provide `*.invalid.json` fixtures, and high-risk path, enum/code, and timestamp fields shall have targeted invalid fixtures when required by `REQ-016`.

## Implementation Gate

Artifact model classes and fixture-based tests shall remain aligned with the schema files above. The JSON schema files remain the contract source of truth.
