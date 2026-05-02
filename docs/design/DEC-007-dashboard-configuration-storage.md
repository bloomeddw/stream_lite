# DEC-007: Dashboard Configuration Storage

## Status

Accepted for v0.1.

## Decision

Dashboard color and layout defaults shall live in versioned YAML at `stream_lite/config/dashboard_presentation.yaml`. FastAPI shall expose the resolved configuration through `GET /config/dashboard-presentation`. v0.1 shall not persist presentation mutations.

## Rationale

A versioned YAML source keeps the presentation configuration easy to review, test, and change without adding a database-backed settings lifecycle before it is needed. Exposing the resolved configuration through the API keeps the Streamlit dashboard aligned with the control-plane contract.

## Requirement Impact

- `REQ-010` defines the dashboard presentation endpoint.
- `REQ-011` defines YAML source, fallback, and validation behavior.
- `REQ-016` requires a versioned dashboard presentation schema.

## Verification Impact

Tests shall validate the YAML schema, endpoint response, required theme tokens, required layout profiles, invalid config failure behavior, and dashboard fallback status.
