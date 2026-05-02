# WP-12 Reference Map: Observability, Metrics, Logging, and Summary Logs

## Purpose

Reduce Codex reasoning for WP-12 by fixing metrics/logging surfaces, units, redaction, operational summaries, health observations, and API/dashboard integration boundaries.

## Scope boundary

WP-12 implements shared observability primitives and integrations. It does not implement business workflow behavior that belongs to watcher, validation, processing, delivery, retry, API, or Streamlit packages.

## Primary requirement IDs

- `SL-OBS-001` through `SL-OBS-027`
- `SL-SEC-015`
- `SL-API-033`
- `SL-UI-012`
- Related log/metric requirements in each capability package

## Read before coding

- `docs/reqs/REQ-012-operational-logging-and-observability.md`
- `docs/operations/prometheus_metrics.md`
- `docs/api/endpoints.md`
- `schemas/api/metrics_summary_response.schema.json`
- `schemas/api/operational_log_list_response.schema.json`
- `app/observability/logging.py`
- `app/repositories/observability.py`
- `app/config/path_policy.py`

## Target modules

| Module | Responsibility |
|---|---|
| `app/observability/metrics.py` | Prometheus metric declarations and helpers. |
| `app/observability/summaries.py` | Operational summary write/read helpers. |
| `app/observability/logging.py` | Redaction and structured log integration improvements. |
| `tests/observability/test_metrics.py` | Metric names, labels, units, and values. |
| `tests/observability/test_summaries.py` | Summary persistence and API-safe shapes. |
| `tests/observability/test_redaction.py` | Secret/path redaction tests. |

## Fixed implementation map

### Metric naming rule

Use prefix `stream_lite_<component>_<measurement>`. Duration metrics use seconds, not milliseconds. Do not introduce `_duration_ms`.

### Required metric families

Implement helpers for documented metrics covering:

- files detected/stable/duplicates
- jobs by state
- retries scheduled/exhausted
- events enqueued/published/dead-lettered
- processing duration seconds
- delivery duration seconds/outcomes
- API request duration seconds
- queue lag
- watcher status/active folders
- Streamlit actions if WP-11 integration exists

### Structured logs

Every structured log should support:

- timestamp
- level
- service
- component
- event
- correlation_id
- job_id and file_id when available
- display_path or safe locator only
- error_code
- retry_attempt
- duration_seconds or duration_ms only if already documented for logs

Never log secrets or raw host paths.

### Summary rows

Use `OperationalLogRepository` and `HealthRepository` for durable dashboard/API summaries. Summary rows are not a replacement for real logs; they are API-visible operator summaries.

## API integration

Metrics summary endpoint should return `metrics_summary_response` shape. Operational logs endpoint should return `operational_log_list_response` shape. If WP-05 already implemented route shells, wire observability helpers behind them without changing route contracts.

## Test checklist

- Metric names match `docs/operations/prometheus_metrics.md`.
- Duration metrics use seconds.
- Metric labels are bounded and documented.
- Secret-looking values are redacted.
- Windows/host paths are redacted or converted to safe display paths.
- Operational summary rows serialize to API schema models.
- Health observations can be inserted/read for dashboard health.

## Out of scope

- New worker logic.
- New route contracts.
- Full production logging backend.

## Verification commands

Run the standard suite plus:

```powershell
pytest tests/observability
```
