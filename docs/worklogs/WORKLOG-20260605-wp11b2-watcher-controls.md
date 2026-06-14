# WORKLOG-20260605-wp11b2-watcher-controls

## Summary

Implemented WP11-B2 watcher helper and render support for route tag normalization, path validation, folder browse view models, route preview ID-to-row mapping, create/edit forms, lifecycle command submission, and reusable command tracking.

## Requirements affected

- REQ-011: `SL-UI-002` through `SL-UI-005`, `SL-UI-013` through `SL-UI-030`, `SL-UI-036`, `SL-UI-038`, `SL-UI-041`, `SL-UI-043`, `SL-UI-044`, `SL-UI-046`
- REQ-002: `SL-FWM-020` through `SL-FWM-031`
- REQ-013: `SL-SEC-013`, `SL-SEC-014`, `SL-SEC-015`

## Files changed

- `streamlit_app/__init__.py`
- `streamlit_app/api_client.py`
- `streamlit_app/commands.py`
- `streamlit_app/pages/watchers.py`
- `tests/streamlit_app/test_api_client.py`
- `tests/streamlit_app/test_command_feedback.py`
- `tests/streamlit_app/test_watcher_controls.py`
- `docs/verification/evidence/streamlit_manual_check.md`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260605-wp11b2-watcher-controls.md`

## Contract/schema usage

- Uses `POST /files/validate-path`, `GET /files/browse`, `POST /watchers`, `PATCH /watchers/{watcher_id}`, `POST /watchers/{watcher_id}/preview-routes`, watcher lifecycle routes, and `GET /commands/{command_id}` only through `StreamLiteApiClient`.
- Uses `RouteTaggedFolderSpec`, `PathValidationResponse`, `FolderBrowseResponse`, `RoutePreviewResponse`, `LifecycleCommandRequest`, `CommandAcceptedResponse`, and `CommandStatusResponse`.
- Adds no backend routes, schemas, migrations, events, repositories, or direct filesystem mutation.

## Tests run

- Explicit-file py_compile equivalent: passed.
- `& '.\.venv\Scripts\pytest.exe' tests\streamlit_app`: 43 passed, 1 warning.
- `python tools\contract_lint.py --write-inventory`: passed.
- `& '.\.venv\Scripts\python.exe' tools\validate_schema_examples.py --write-evidence`: 169 examples passed, 0 failed.
- `& '.\.venv\Scripts\pytest.exe' --basetemp <repo-local .tmp path>`: 433 passed, 1 warning.

## Manual evidence status

- `docs/verification/evidence/streamlit_manual_check.md` created with runtime checks marked `not run`.

## Assumptions

- Lifecycle start follows the backend/control-matrix contract: `CREATED`, `STOPPED`, or `ERROR` with green preview. Resume handles `PAUSED`.
- Existing API error payloads are operator-safe and provide correlation IDs when available.

## Gaps

- Unsaved create-form route preview is constrained by the current documented `POST /watchers/{watcher_id}/preview-routes` route requiring an existing watcher ID. The create API remains authoritative for route validation on save.
- Manual browser/runtime verification was not run.

## Rollback notes

Revert the listed Streamlit helper, API-client, tests, evidence, and worklog/index files. No database or backend rollback is required.

## Next step

WP11-B2 retry controls.
