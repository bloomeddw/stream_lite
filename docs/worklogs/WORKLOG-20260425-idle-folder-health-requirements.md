# WORKLOG-20260425-idle-folder-health-requirements

## Summary

Updated the requirements baseline to capture idle watcher behavior, source and destination folder reachability, Streamlit folder browse controls, filepath entry controls, green/yellow/red health dots, API support for folder browsing and validation, output delivery fault visibility, observability, and verification coverage.

## Files Changed

- `stream_lite/docs/master_overview.md`
- `stream_lite/docs/reqs/INDEX.md`
- `stream_lite/docs/reqs/CURRENT_REQUIREMENTS_RECAP.md`
- `stream_lite/docs/reqs/REQ-002-folder-watch-management.md`
- `stream_lite/docs/reqs/REQ-003-file-detection-and-ingestion.md`
- `stream_lite/docs/reqs/REQ-008-output-delivery.md`
- `stream_lite/docs/reqs/REQ-010-fastapi-control-plane.md`
- `stream_lite/docs/reqs/REQ-011-streamlit-command-center.md`
- `stream_lite/docs/reqs/REQ-012-operational-logging-and-observability.md`
- `stream_lite/docs/reqs/REQ-014-verification-and-acceptance.md`

## Duplicate Files Removed From Cleaned Baseline

- `stream_lite/docs/reqs/REQ-006-processing-orchestration.md`
- `stream_lite/docs/reqs/REQ-012-dockerized-runtime.md`

These files were duplicate mixed-version requirement drafts from the earlier cleanup. Their unique content was already migrated into the active requirements baseline.

## Requirements Affected

- Folder watch management: `SL-FWM-013` through `SL-FWM-019`
- File detection and ingestion: `SL-FDI-013` through `SL-FDI-014`
- Output delivery: `SL-OUT-013` through `SL-OUT-015`
- FastAPI control plane: `SL-API-013` through `SL-API-015`
- Streamlit command center: `SL-UI-013` through `SL-UI-021`
- Operational logging and observability: `SL-OBS-013` through `SL-OBS-014`
- Verification and acceptance: `SL-VER-013` through `SL-VER-015`

## Decisions Applied

No architecture-changing decision was applied. The additions refine the existing file-ingestion demo by making idle behavior and folder reachability explicit and testable. The dashboard remains API-backed and does not write directly to PostgreSQL.

## Tests and Verification

Documentation-level verification performed:

- Confirmed all new requirements use stable `SL-*` IDs.
- Confirmed every new requirement has a verification reference.
- Confirmed affected capabilities have measurable acceptance criteria or nonfunctional targets.
- Confirmed no new environment variables were introduced.
- Confirmed new Streamlit controls map to API endpoints.

Implementation verification still required:

- `V-SL-DEMO-011`: idle watcher with empty source folders.
- `V-SL-DEMO-012`: source/destination health dots.
- `V-SL-DEMO-013`: dashboard folder browse flow.

## Assumptions

- Folder browsing means selecting from mounted, API-approved folders inside the configured allowlist; browser-native arbitrary filesystem access is not assumed in the Dockerized demo.
- Yellow indicates pending validation, degraded, empty/idle, or non-blocking warnings; red indicates blocked source transfer or blocked destination delivery.
- A started watcher may be healthy and idle without being considered failed.

## Gaps

- Detailed API schemas for `/files/browse` and `/files/validate-path` still need to be added under `stream_lite/docs/api/`.
- Prometheus metric names for folder health and watcher idle/blocked states still need to be added under operations metrics documentation.
- Streamlit control-to-state-transition matrix should be expanded in the next requirements pass.

## Rollback Notes

Rollback by restoring the listed requirement files from the previous baseline and removing this worklog. No code or environment changes are included in this patch.

## Next Step

Create API route specs, dashboard control matrix, and Prometheus metric catalog entries for folder browsing, path validation, and folder health indicators.
