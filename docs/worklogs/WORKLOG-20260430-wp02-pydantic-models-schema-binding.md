# WORKLOG-20260430-wp02-pydantic-models-schema-binding

## Summary

Implemented WP-02 only: requirements-backed Pydantic models for API, event, and artifact contracts; schema-to-model registries; schema-binding tests over valid and invalid fixtures; artifact schema documentation; and contract-lint/schema-example coverage updates required to keep JSON schemas authoritative. Pydantic was introduced as a runtime dependency in `requirements.txt`, JSON schemas remained the source of truth, the schema/example fixture inventory increased to `169` examples, temporary vendor troubleshooting folders were removed before handoff, repo hygiene was confirmed before WP-03, and WP-03 was not started.

## Files changed

- Runtime model modules:
  - `app/_schema_types.py`
  - `app/api/schemas/__init__.py`
  - `app/api/schemas/api_models.py`
  - `app/events/__init__.py`
  - `app/events/models.py`
  - `app/artifacts/__init__.py`
  - `app/artifacts/models.py`
- Contract and dependency support:
  - `.gitignore`
  - `requirements.txt`
  - `requirements-dev.txt`
  - `tools/contract_lint.py`
- Schema and schema-doc updates:
  - `docs/schemas/INDEX.md`
  - `docs/schemas/api_schemas.md`
  - `docs/schemas/events.md`
  - `docs/schemas/artifact_schemas.md`
  - `schemas/api/*.schema.json`
  - `schemas/events/*.schema.json`
  - `schemas/artifacts/*.schema.json`
- Fixture and verification updates:
  - `schemas/examples/api/*.json`
  - `schemas/examples/events/*.json`
  - `schemas/examples/artifacts/*.json`
  - `tests/schemas/test_pydantic_schema_binding.py`
  - `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
  - `docs/verification/evidence/schema_fixture_validation.md`
  - `docs/verification/evidence/sphinx_build.txt`
  - `docs/worklogs/INDEX.md`
  - `docs/worklogs/WORKLOG-20260430-wp02-pydantic-models-schema-binding.md`

## Requirements affected

- `SL-DCT-001` through `SL-DCT-033`
- `SL-API-031` through `SL-API-040`
- `SL-EVT-001` through `SL-EVT-023`
- Related artifact-contract rows in `docs/schemas/artifact_schemas.md`
- Reused WP-01 shared error, path-safety, and config contract requirements where the schema-bound models depend on those primitives

## Contract/schema usage

- `schemas/api/*.schema.json` remained the authority for API request and response shapes; the API registry now covers every active API schema file.
- `schemas/events/*.schema.json` remained the authority for event envelopes and payloads; the event registry now covers every active event schema file.
- `schemas/artifacts/*.schema.json` remained the authority for persisted artifact payloads; the artifact registry now covers every active artifact schema file.
- Valid fixtures under `schemas/examples/api/`, `schemas/examples/events/`, and `schemas/examples/artifacts/` validate through the matching Pydantic model and preserve schema-facing field names through `model_dump(mode="json", exclude_unset=True)`.
- Invalid fixture classes `invalid`, `invalid_enum`, `invalid_timestamp`, and `invalid_path` fail model validation as expected where the schema contract requires them.
- The restored schema files were rechecked as valid UTF-8 JSON without BOM, and retained closed-object constraints plus timestamp, enum/code, and path/locator safeguards instead of weakening the contracts.

## Decisions applied

- Use shared typed primitives in `app/_schema_types.py` for RFC 3339 UTC timestamps, route tags, error codes, SHA-256 hex strings, and safe path/locator validation so the Python models mirror the JSON schema constraints instead of softening them.
- Keep JSON schemas authoritative and repair model code, fixtures, or supporting lint rules when mismatches appear.
- Keep `ProcessingSummary` extensible because `schemas/artifacts/processing_summary.schema.json` explicitly allows additional properties; keep the other schema-root models closed where the schema sets `additionalProperties: false`.
- Treat temporary folders `.pytest_vendor/`, `pytest_vendor/`, and `wheelhouse/` as troubleshooting artifacts only; exclude them in `.gitignore`, ignore them in contract linting, and remove them before handoff.
- Stay inside WP-02 scope only. No FastAPI route handlers, database code, migrations, repositories, workers, dispatchers, watcher services, validation/processing/delivery runtime services, retry schedulers, Streamlit pages, or WP-03 implementation work were started.

## Verification commands and results

Verification ran from `C:\Users\asosa\stream_lite` in a temporary repo-local `.venv` created only for dependency-backed checks:

```powershell
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/contract
pytest tests/config tests/api tests/observability
pytest tests/schemas
```

Results:

- `python -S tools/contract_lint.py --write-inventory`: passed.
- `python tools/validate_schema_examples.py --write-evidence`: passed with `169` examples validated, `169` passed, and `0` failed.
- `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`: passed with Sphinx exit code `0`.
- `pytest tests/contract`: passed with `3 passed`.
- `pytest tests/config tests/api tests/observability`: passed with `16 passed`.
- `pytest tests/schemas`: passed with `213 passed`.
- Pytest emitted cache-path warnings because transient cache directories inherited restrictive permissions in this workspace; the final hygiene pass removed repo-side cache output before handoff.

## Assumptions

- The workspace snapshot is a filesystem export rather than an active Git checkout, so verification and hygiene checks rely on direct filesystem inspection instead of `git status`.
- The repo-local `.venv` is a temporary verification environment only and is removed before handoff so generated environment content does not remain in the working tree.

## Gaps

- No known WP-02 gaps remain.

## Rollback notes

Revert the WP-02 model modules, schema/example updates, dependency declarations, contract-lint changes, schema tests, worklog index entry, and this worklog to return to the WP-01 baseline. If rollback restores temporary verification artifacts such as `.venv/`, `docs/_build/`, `.pytest_cache/`, `__pycache__/`, `*.pyc`, `.pytest_vendor/`, `pytest_vendor/`, `wheelhouse/`, `.tmp/`, or `pytest-cache-files-*`, remove them again before any subsequent handoff.

## Next step

Temporary vendor/cache troubleshooting artifacts were removed before handoff. Repo hygiene was confirmed before WP-03, and WP-03 must be started separately.
