# WP-11 Reference Map: Streamlit Command Center

## Purpose

Reduce Codex reasoning for WP-11 by fixing the Streamlit page map, API-only data access rule, controls, polling behavior, theme/layout use, and evidence expectations.

## Scope boundary

WP-11 implements an operator dashboard that reads and controls Stream Lite through the FastAPI control plane. Streamlit must not write directly to the database or Redis in MVP.

## Primary requirement IDs

- `SL-UI-001` through `SL-UI-030`
- `SL-API-031` through `SL-API-040`
- `SL-OBS-009`, `SL-OBS-010`
- `SL-SEC-010`, `SL-SEC-011` where operator path display/control is involved

## Read before coding

- `docs/reqs/REQ-011-streamlit-command-center.md`
- `docs/streamlit/control_matrix.md`
- `docs/api/endpoints.md`
- `docs/schemas/api_schemas.md`
- `docs/design/DEC-002-centralized-dashboard-presentation.md`
- `docs/design/DEC-007-dashboard-configuration-storage.md`
- `schemas/api/dashboard_presentation_response.schema.json`
- `app/api/schemas/api_models.py`

## Target modules

| Module | Responsibility |
|---|---|
| `streamlit_app/__init__.py` | Package marker. |
| `streamlit_app/api_client.py` | Typed API client using documented API schemas. |
| `streamlit_app/theme.py` | Apply dashboard presentation response tokens. |
| `streamlit_app/layout.py` | Page/section layout helpers. |
| `streamlit_app/main.py` | Navigation shell. |
| `streamlit_app/pages/health.py` | Health/dependency/metrics summary view. |
| `streamlit_app/pages/watchers.py` | Watcher list/detail/config/route preview/start/stop controls. |
| `streamlit_app/pages/jobs.py` | Job list/detail/history/retry controls. |
| `streamlit_app/pages/events.py` | Event list/filter view. |
| `streamlit_app/pages/quarantine.py` | Quarantine/validation failure visibility. |
| `streamlit_app/pages/outputs.py` | Output/delivery status visibility. |
| `streamlit_app/pages/logs.py` | Operational log summary visibility. |
| `streamlit_app/pages/config.py` | Presentation/config display and safe folder browse controls. |
| `tests/streamlit_app/` | API client, theme/layout, command polling tests. |

## Fixed implementation map

### API-only rule

All Streamlit data access must go through FastAPI endpoints implemented in WP-05. Do not import repositories or database sessions in Streamlit code.

### Page-to-API map

| Page | Required API use |
|---|---|
| Health | `GET /health`, dependency health, metrics summary. |
| Watchers | list/detail/create/patch/start/stop/route-preview/folder-browse/path-validation. |
| Jobs | list/detail/history/retry command and command status polling. |
| Events | `GET /events` with filters/pagination. |
| Quarantine | job/validation/quarantine API outputs already exposed by WP-05. |
| Outputs | job detail/output delivery summaries already exposed by WP-05. |
| Logs | operational log list endpoint. |
| Config | dashboard presentation endpoint and safe config display. |

### Command behavior

For commands returning `202 Accepted`:

1. Show immediate accepted state.
2. Poll command status endpoint.
3. Show success/failure using `command_status_response` and `standard_error` envelope.
4. Do not assume success from `202`.

### Theme/layout

Use `dashboard_presentation_response` for theme tokens, status-dot colors, refresh intervals, and layout sections. Do not hard-code business logic in theme helpers.

## Test checklist

- API client serializes/deserializes documented schemas.
- Command polling stops on `succeeded`, `failed`, or `expired`.
- Theme helper uses dashboard presentation tokens.
- Watcher controls call API endpoints and do not use repositories directly.
- Retry button only appears for API-reported eligible states, not guessed local state.
- Safe paths are displayed; raw host paths are not introduced.

## Manual evidence checklist

Capture in `docs/verification/evidence/streamlit_manual_check.md` or equivalent:

- Health visible.
- Watchers visible and controllable.
- Jobs visible.
- Events visible.
- Validation/quarantine visible.
- Outputs visible.
- Logs/summary visible if supported by endpoint.
- Metrics summaries visible.
- Theme/layout configuration applied.

## Out of scope

- Direct DB/Redis access.
- New FastAPI route contracts.
- Worker implementation.

## Verification commands

Run the standard suite plus:

```powershell
pytest tests/streamlit_app
```

Manual Streamlit evidence is acceptable where UI automation is not available.
