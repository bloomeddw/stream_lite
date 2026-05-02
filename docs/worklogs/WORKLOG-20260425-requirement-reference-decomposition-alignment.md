# WORKLOG-20260425-requirement-reference-decomposition-alignment

## Summary

Performed a requirements-first alignment pass focused on requirement ID references, endpoint/event traceability, and decomposition levels. The pass inventories requirement references across docs, schemas, and `.env.example`; resolves missing event requirement IDs; introduces L1/L2/L3 decomposition rules; decomposes FastAPI endpoint contracts into L2 and L3 trace requirements; and retires the standalone `REQ-018` decomposition file by migrating its readiness requirements into `REQ-000`.

## Files changed

- `stream_lite/docs/api/endpoints.md`
- `stream_lite/docs/reqs/REQ-000-requirements-quality-and-ambiguity-control.md`
- `stream_lite/docs/reqs/REQ-005-event-streaming.md`
- `stream_lite/docs/reqs/REQ-010-fastapi-control-plane.md`
- `stream_lite/docs/reqs/INDEX.md`
- `stream_lite/docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
- `stream_lite/docs/verification/verification_matrix.md`
- `stream_lite/docs/worklogs/DELETE_MANIFEST-20260425-retire-req018-decomposition-file.md`
- `stream_lite/docs/worklogs/WORKLOG-20260425-requirement-reference-decomposition-alignment.md`

## Files retired

- `stream_lite/docs/reqs/REQ-018-contract-decomposition-and-implementation-readiness.md`

Because zip extraction does not reliably delete existing files, the deletion is captured in `DELETE_MANIFEST-20260425-retire-req018-decomposition-file.md`.

## Requirements affected

- `SL-REQ-005` through `SL-REQ-008`: added requirement reference accountability and L1/L2/L3 decomposition rules.
- `SL-DECOMP-001` through `SL-DECOMP-010`: migrated from retired `REQ-018` into `REQ-000`.
- `SL-EVT-016` through `SL-EVT-023`: added L2 event-type decomposition, including the previously unresolved `SL-EVT-017`, `SL-EVT-022`, and `SL-EVT-023` references.
- `SL-API-031` through `SL-API-040`: added L2 endpoint alignment and synchronization requirements.
- `SL-API-041` through `SL-API-050`: added L3 implementation trace requirements for initial API route handlers/functions.
- `SL-EVT-015` and `SL-API-032`: aligned `GET /events` endpoint references across API and requirement docs.

## Decisions applied

- Decomposition belongs in the owning requirement file, not a standalone `REQ-018` file.
- The baseline uses three levels:
  - L1: capability intent and acceptance.
  - L2: explicit contracts for APIs, schemas, events, states, logs, metrics, env vars, retries, and policies.
  - L3: named implementation surfaces/functions/handlers with verification traceability.
- Verification IDs prefixed with `V-SL-` are not requirement IDs and shall not trigger missing requirement creation.

## Verification performed

- Static scan of requirement-like references using `SL-<CAPABILITY>-<NNN>` while excluding `V-SL-*` verification IDs.
- Cross-reference of scanned IDs against active first-column requirement rows in `docs/reqs/REQ-*.md`.
- Duplicate first-column requirement row check.
- Manual review of previously missing references:
  - `SL-EVT-017`
  - `SL-EVT-022`
  - `SL-EVT-023`
- Manual review of `REQ-010` duplicate `SL-API-022` through `SL-API-030` rows; duplicate endpoint decomposition IDs were renumbered to `SL-API-031` through `SL-API-040` and L3 trace rows were added as `SL-API-041` through `SL-API-050`.

## Verification result

- Unique requirement references scanned: 401.
- Unique active requirement rows found: 401.
- Referenced requirement IDs without active rows: 0.
- Duplicate active first-column requirement rows found after patch: 0.

## Assumptions

- Existing broad capability rows remain L1 even when the row table does not yet have a `Level` column.
- New and materially modified decomposition rows explicitly carry level context either in the row or in the section heading.
- Handler/module names in L3 API rows are expected implementation surfaces and may be changed later only through an explicit design decision or requirement update.

## Gaps and next steps

- Extend L3 traceability beyond the initial API route handlers into watcher, validator, processor, delivery, retry scheduler, event dispatcher, Streamlit, and Sphinx surfaces.
- Normalize remaining metric naming differences project-wide if the team chooses `_seconds` instead of `_ms`; this patch aligned `REQ-010` with the current endpoint and metrics catalog naming rather than changing the metric contract.
- Add a lightweight static lint script later to generate `REQUIREMENT_REFERENCE_INVENTORY.md` automatically.

## Rollback notes

To roll back, restore the previous versions of the changed requirement and API docs, remove `REQUIREMENT_REFERENCE_INVENTORY.md`, restore `REQ-018-contract-decomposition-and-implementation-readiness.md`, and remove the new worklog/delete manifest. Rolling back will reintroduce unresolved event requirement references and duplicate API requirement IDs.
