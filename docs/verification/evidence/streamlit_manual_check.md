# Streamlit Manual Check Evidence

## Environment

- Date: 2026-06-05
- Commit/source package: local working tree from `stream_lite__20260605_1555.zip`
- API base URL: not run
- Dashboard URL: not run
- Operator: Codex

## Checks

| Check | Result | Evidence / notes |
|---|---|---|
| Health visible | not run | Runtime dashboard was not started in this verification pass. |
| Watchers visible | not run | Runtime dashboard was not started in this verification pass. |
| Watcher create form visible | not run | Runtime dashboard was not started in this verification pass. |
| Source browse visible | not run | Runtime dashboard was not started in this verification pass. |
| Destination browse visible | not run | Runtime dashboard was not started in this verification pass. |
| Path validation status dot visible | not run | Runtime dashboard was not started in this verification pass. |
| Route tag normalization visible | not run | Runtime dashboard was not started in this verification pass. |
| Route preview visible | not run | Runtime dashboard was not started in this verification pass. |
| Start/pause/resume/stop controls visible | not run | Runtime dashboard was not started in this verification pass. |
| Command accepted card visible | not run | Runtime dashboard was not started in this verification pass. |
| Command terminal status visible | not run | Runtime dashboard was not started in this verification pass. |
| Jobs visible | not run | Runtime dashboard was not started in this verification pass. |
| Job detail/history visible | not run | Runtime dashboard was not started in this verification pass. |
| Retry form visible for failed job | not run | Runtime dashboard was not started in this verification pass. |
| Retry API rejection displays safe error | not run | Runtime dashboard was not started in this verification pass. |
| Events visible | not run | Runtime dashboard was not started in this verification pass. |
| Validation/quarantine visible | not run | Runtime dashboard was not started in this verification pass. |
| Outputs visible | not run | Runtime dashboard was not started in this verification pass. |
| Logs visible | not run | Runtime dashboard was not started in this verification pass. |
| Metrics summary visible | not run | Runtime dashboard was not started in this verification pass. |
| Theme/layout config visible | not run | Runtime dashboard was not started in this verification pass. |

## Gaps

- Manual Streamlit runtime was not launched during this verification pass.
- `POST /watchers/{watcher_id}/preview-routes` requires an existing watcher ID; unsaved create-form preview remains constrained by the current documented API route.

## Follow-up

- Run FastAPI and Streamlit locally and update each check with pass/fail evidence.
