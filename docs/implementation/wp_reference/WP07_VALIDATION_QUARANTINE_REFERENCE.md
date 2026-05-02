# WP-07 Reference Map: Validation and Quarantine

## Purpose

Reduce Codex reasoning for WP-07 by fixing validator, quarantine, event, artifact, repository, and test boundaries.

## Scope boundary

WP-07 validates stable registered files, persists validation attempts, quarantines invalid files, writes quarantine record artifacts, updates job state, and enqueues validation/quarantine events.

WP-07 must not implement watcher polling, processing, delivery, retry scheduling, API routes, or Streamlit pages.

## Primary requirement IDs

- `SL-VAL-001` through `SL-VAL-024`
- `SL-JOB-038`
- `SL-JOB-039`
- `SL-LIFE-007`
- `SL-SEC-012`
- `SL-OBS-004`
- `SL-EVT-004`, `SL-EVT-005`
- `SL-DCT-001` through `SL-DCT-033` where schema validation is reused

## Read before coding

- `docs/reqs/REQ-004-file-validation-and-quarantine.md`
- `docs/operations/quarantine_policy.md`
- `docs/operations/fault_tolerance.md`
- `docs/reqs/REQ-006-job-metadata-and-state.md`
- `app/repositories/validation.py`
- `app/repositories/jobs.py`
- `app/config/path_policy.py`
- `app/events/outbox.py`
- `schemas/events/file_validated.schema.json`
- `schemas/events/file_quarantined.schema.json`
- `schemas/artifacts/quarantine_record.schema.json`

## Target modules

| Module | Responsibility |
|---|---|
| `app/validation/__init__.py` | Export WP-07 validation surfaces. |
| `app/validation/validator.py` | Rule-based validation and validation result object. |
| `app/validation/quarantine.py` | Safe quarantine copy and quarantine record artifact writing. |
| `tests/validation/test_validator.py` | Extension/size/readability/rule result tests. |
| `tests/validation/test_quarantine.py` | Safe copy, artifact, and path-safety tests. |
| `tests/validation/test_validation_flow.py` | Repository + event enqueue integration tests. |

## Fixed implementation map

### Validator rules

Implement validation as deterministic rule checks:

1. Allowed extension.
2. Maximum size.
3. Readability.
4. Basic non-empty file check only if required by existing requirements.

Return a structured validation result:

- `status`: `valid` or `invalid`
- `reason_codes`: list of `ErrorCode`
- `operator_message`: safe operator-facing message
- `duration_seconds`
- `rules_applied`

Do not parse full business data formats unless explicitly required.

### Valid file flow

1. Create validation attempt row with status `valid`.
2. Update job state to `VALIDATED` or next documented state.
3. Append job state history.
4. Enqueue `file.validated`.
5. Do not start processing in WP-07.

### Invalid file flow

1. Create validation attempt row with status `invalid`.
2. Copy file to quarantine root using the documented quarantine path layout.
3. Write `quarantine_record.json` matching `schemas/artifacts/quarantine_record.schema.json`.
4. Persist quarantine record row.
5. Update job state to `QUARANTINED` or documented invalid/quarantine state.
6. Append job state history.
7. Enqueue `file.quarantined`.
8. Do not schedule retry for validation failures unless current retry policy explicitly requires it.

## Events/artifacts produced

| Output | Producer | Notes |
|---|---|---|
| `file.validated` | `validator` | For valid files only. |
| `file.quarantined` | `validator` | For invalid files quarantined immediately. |
| `quarantine_record.json` | `QuarantineService` | Must validate against artifact schema. |

## Repository use

| Repository | Required WP-07 use |
|---|---|
| `ValidationRepository` | Persist validation attempts and quarantine records. |
| `JobRepository` | Load/update job state and append state history. |
| `EventOutboxRepository` | Indirectly via `app/events/outbox.py`. |

## Test checklist

- Valid extension/size/readable file returns valid result.
- Disallowed extension returns invalid with uppercase reason code.
- Oversized file returns invalid without reading full content.
- Missing/unreadable file returns invalid or recoverable failure as documented.
- Invalid file is copied to quarantine root using safe path only.
- Quarantine artifact validates against JSON schema and Pydantic artifact model.
- Valid flow enqueues `file.validated` and does not quarantine.
- Invalid flow persists quarantine record and enqueues `file.quarantined`.
- Unsafe source path is rejected and never logged as raw host path.

## Out of scope

- Starting processing worker.
- Retry scheduler execution.
- Delivery worker.
- API/Streamlit controls.

## Verification commands

Run the standard suite plus:

```powershell
pytest tests/validation
```
