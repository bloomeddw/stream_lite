# API and Event Field Name Review Before Pydantic Generation

## Purpose

This review freezes field naming decisions before Pydantic model generation begins. The goal is to keep API documents, JSON schema files, event inventory, example fixtures, and database/migration contracts aligned.

## Naming Rules

| Area | Decision | Rationale | Requirement IDs |
|---|---|---|---|
| JSON field case | API, event, artifact, and example JSON fields shall use `snake_case`. | Matches Python/Pydantic names and avoids alias ambiguity during implementation. | SL-DCT-023 |
| IDs | Identifier fields shall end in `_id` and use UUID string format unless a schema explicitly states otherwise. | Keeps source, watcher, job, command, event, and attempt references searchable and consistent. | SL-DCT-008, SL-JOB-002 |
| Command target fields | Command API responses shall use `target_resource_type` and `target_resource_id`. | Aligns API schemas with the command record schema in `SL-DCT-017`. | SL-DCT-016, SL-DCT-017 |
| Event envelope | Event schemas shall use `schema_version`, `event_type`, `event_id`, `idempotency_key`, `correlation_id`, `occurred_at`, `producer`, `job_id`, `watcher_id`, `attempt_number`, and `payload`. | Gives producers and consumers a single envelope shape. | SL-EVT-001, SL-DCT-023 |
| Timestamps | Serialized API/event timestamps shall be RFC 3339 UTC strings ending in `Z`. | Prevents local timezone ambiguity. | SL-DCT-009 |
| Durations | API/event duration fields shall be numeric seconds and end with `_seconds` or `duration_seconds`. | Matches the project Prometheus convention. | SL-OBS-025 |
| Paths | Operator-facing paths shall use `display_path`, `normalized_path`, `container_locator`, `quarantine_locator`, or `finalized_locator`; host-only absolute path fields are not allowed. | Keeps demo paths safe and portable. | SL-DCT-010, SL-SEC-014 |
| Error fields | API and command error objects shall use `error_code`, `message`, `field`, `resource_id`, `current_state`, and `correlation_id`. | Aligns with `docs/api/errors.md` and command polling responses. | SL-API-020, SL-DCT-023 |

## Review Results

| Contract area | Result | Follow-up |
|---|---|---|
| API schema names | Each endpoint request/success schema name maps to a JSON schema file named by snake_case conversion. | Enforced by `tools/contract_lint.py`. |
| API command response fields | `target_type`/`target_id` were renamed to `target_resource_type`/`target_resource_id`. | Pydantic models shall use the renamed fields without aliases unless a future compatibility requirement is added. |
| Standard error schema | `StandardError` is documented in `docs/schemas/api_schemas.md` and has valid/invalid examples. | FastAPI exception handlers shall emit compatible envelopes later. |
| Event schema names | Each event row maps to one `schemas/events/*.schema.json` file, and the schema `event_type.const` matches the inventory value. | Enforced by `tools/contract_lint.py`. |
| Examples | Every active API and event schema has one valid and one invalid example under `schemas/examples`. | Invalid examples currently focus on missing required fields; deeper invalid enum/timestamp/path fixtures can be added after model generators are selected. |

## Implementation Gate

Pydantic model generation shall not begin until `python -S tools/contract_lint.py --write-inventory` passes and this review remains current with the schema files.
