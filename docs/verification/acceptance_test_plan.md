# Acceptance Test Plan

## ATP-001 Local Stack Smoke

Start Docker Compose, confirm `/health`, `/health/dependencies`, Streamlit availability, Redis persistence, and PostgreSQL persistence.

## ATP-002 Watcher Configuration and Route Preview

Create a watcher with two sources and three destinations using tags `A`, `B`, and `A;B`. Verify normalization, match preview, unmatched warnings, and blocked start for no matching destination.

## ATP-003 Happy Path File Lifecycle

Drop a valid CSV file into a watched source. Verify job states from `DETECTED` through `COMPLETED`, emitted events, processing summary, output manifest, metrics, and dashboard visibility.

## ATP-004 Invalid File Quarantine

Drop invalid JSON and unsupported extension fixtures. Verify validation failure, quarantine copy, `quarantine_record.json`, source unchanged, non-retryable job response, dashboard warning, and metric increments.

## ATP-005 Retry and Recovery

Simulate processing and delivery transient failures. Verify retry schedule, backoff, eventual success or exhausted failure, command status, logs, metrics, and no duplicate finalized outputs.

## ATP-006 Restart and Outbox Recovery

Restart API, watcher, validator, processor, delivery, Redis, and PostgreSQL at stage boundaries. Verify reconciliation and outbox publication recover without duplicate jobs or outputs.

## ATP-007 Control Plane UX Contract

Use Streamlit controls only. Verify each mutation calls FastAPI, shows command status, disables invalid actions, and displays operator-safe errors.

## ATP-008 Documentation and Contract Build

Run docs/schema lint, Sphinx static build, and verification matrix completeness checks.
