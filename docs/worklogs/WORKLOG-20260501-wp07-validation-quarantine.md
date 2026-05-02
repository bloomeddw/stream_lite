# WORKLOG-20260501-wp07-validation-quarantine

## Summary

Implemented the WP-07 validation/quarantine slice with deterministic file validation, copy-only quarantine handling, validation-stage orchestration, quarantine artifact/schema alignment, and a focused `tests/validation/` suite.

## Requirements affected

- `SL-VAL-001` through `SL-VAL-024`
- `SL-JOB-038`
- `SL-JOB-039`
- `SL-EVT-019`
- `SL-LIFE-004`
- `SL-LIFE-005`
- `SL-OBS-004`
- `SL-OBS-005`
- `SL-OBS-023`
- `SL-OBS-024`
- `SL-SEC-013`
- `SL-SEC-014`
- `SL-DCT-010`
- `SL-DCT-012`
- `SL-DCT-023`
- `SL-DCT-032`

## Files changed

- `AGENTS.md`
- `RULES.md`
- `app/artifacts/models.py`
- `app/validation/__init__.py`
- `app/validation/validator.py`
- `app/validation/quarantine.py`
- `app/validation/service.py`
- `tests/validation/test_validator.py`
- `tests/validation/test_quarantine.py`
- `tests/validation/test_validation_flow.py`
- `schemas/artifacts/quarantine_record.schema.json`
- `schemas/examples/events/file_quarantined.valid.json`
- `schemas/examples/events/file_quarantined.invalid_enum.json`
- `schemas/examples/events/file_quarantined.invalid_path.json`
- `schemas/examples/events/file_quarantined.invalid_timestamp.json`
- `schemas/examples/artifacts/quarantine_record.valid.json`
- `schemas/examples/artifacts/quarantine_record.invalid.json`
- `schemas/examples/artifacts/quarantine_record.invalid_enum.json`
- `schemas/examples/artifacts/quarantine_record.invalid_path.json`
- `schemas/examples/artifacts/quarantine_record.invalid_timestamp.json`
- `docs/operations/quarantine_policy.md`
- `docs/schemas/artifact_schemas.md`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260501-wp07-validation-quarantine.md`

## Implementation notes

- Added deterministic validation rules in the required order: path allowlist, existence, readability, size, extension, non-empty, and structured-format checks.
- Supported WP-07 MVP extensions are `.csv`, `.json`, and `.txt`; structured-format failures collapse to `SCHEMA_INVALID`.
- Quarantine copies files into `{quarantine_root}/watcher_id=<watcher_id>/date=YYYY-MM-DD/job_id=<job_id>/` and writes `quarantine_record.json` beside the copied file without moving or deleting the source.
- Validation orchestration transitions jobs `REGISTERED -> VALIDATING -> VALIDATED` for accepted files and `REGISTERED -> VALIDATING -> INVALID -> QUARANTINED` for rejected files.
- `file.validated` and `file.quarantined` are enqueued through the existing outbox with producer `validator`, schema version `1.0.0`, and preserved correlation IDs.
- Quarantine artifact/schema/examples were aligned so artifact payloads carry both safe display paths and container-safe quarantine locators.
- Guardrail files were aligned first to explicitly forbid cleanup deletion, reset, and worktree-destructive packaging behavior for WP-07 continuation.

## Tests run

Syntax check passed with the available system Python:

```powershell
python -m py_compile app\validation\__init__.py app\validation\validator.py app\validation\quarantine.py app\validation\service.py app\artifacts\models.py tests\validation\test_validator.py tests\validation\test_quarantine.py tests\validation\test_validation_flow.py
```

Validation pytest was blocked by missing test dependency support in the available Python environment:

```powershell
python -m pytest tests/validation -q
```

Result:

```text
C:\Python314\python.exe: No module named pytest
```

The repo-local `.venv` requested by the prompt was not present under `C:\Users\asosa\stream_lite\.venv`.

## Assumptions

- The current repository state is the source of truth after the prior WP-07 damage, and missing runtime files were reimplemented from the documented contracts.
- A path-allowlist failure should remain non-retryable and operator-safe, so `PATH_POLICY_VIOLATION` handling was preserved even though the prompt focused the MVP reason-code list on file/format cases.
- The existing repo has not yet introduced a shared metrics helper, so WP-07 observability was implemented through structured logs only.

## Gaps

- Required verification is not complete because the requested `.venv` is missing and the available Python environment does not have `pytest`.
- The full required command set was not run: `contract_lint`, schema-example evidence generation, Sphinx verification, and all pytest suites remain blocked behind the missing test environment.
- No retained evidence artifacts were updated because the verification commands could not be completed.

## Rollback notes

- Revert `app/validation/`, `tests/validation/`, the quarantine schema/example/doc updates, and this worklog/index entry to remove the WP-07 implementation slice.
- No repository cleanup or file deletion is required for rollback; quarantine behavior is copy-only and source files remain untouched.

## Next step

Restore the repo-local `.venv` or provide an equivalent Python environment with `pytest` and the contract-tool dependencies, then rerun the required WP-07 verification suite and regenerate the evidence artifacts before starting WP-08.
