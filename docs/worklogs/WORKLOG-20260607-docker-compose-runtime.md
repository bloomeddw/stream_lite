# 2026-06-07 Docker Compose Runtime Patch

## Summary

Added a Docker Compose runtime entrypoint for the current Stream Lite archive so a developer can build and start the API, dashboard, PostgreSQL, and Redis Streams profile with Docker Compose.

## Files Changed

- `docker-compose.yml`
- `Dockerfile`
- `.dockerignore`
- `docker/streamlit_launcher.py`
- `requirements.txt`
- `docs/worklogs/WORKLOG-20260607-docker-compose-runtime.md`

## Requirements Addressed

- `SL-RUN-001` — compose file starts the local stack with one command.
- `SL-RUN-002` — FastAPI host port is exposed from `STREAM_LITE_API_PORT`, default `8000`.
- `SL-RUN-003` — Streamlit host port is exposed from `STREAM_LITE_DASHBOARD_PORT`, default `8501`.
- `SL-RUN-004` — PostgreSQL persists to `stream_lite_postgres_data`.
- `SL-RUN-005` — Redis uses append-only persistence with `stream_lite_redis_data`.
- `SL-RUN-006` — source, output, and quarantine roots are mounted explicitly.
- `SL-RUN-008` — Postgres, Redis, API, and dashboard services include health checks.
- `SL-RUN-011` / `SL-RUN-017` — stable compose service names are provided for `api`, `dashboard`, `postgres`, and `redis`; `migrate` is included as a one-shot database migration service.
- `SL-RUN-016` — Docker named volumes use the `stream_lite_` prefix.
- `SL-RUN-018` — long-running service logs are available through `docker compose logs`.

## Decisions

- Used Redis Streams only, consistent with `DEC-003`.
- Used the existing Python implementation image for API and dashboard services.
- Added `docker/streamlit_launcher.py` so Streamlit resolves the API through the compose service hostname `api` without adding a new undocumented `STREAM_LITE_*` environment variable.
- Added runtime-only dependencies needed by the container entrypoints: `uvicorn[standard]`, `streamlit`, and `psycopg2-binary`.

## Tests and Verification

- `docker compose config --services`
- `python -m pytest tests/config/test_settings.py tests/streamlit_app/test_theme_layout.py`

## Assumptions

- The active v0.1 executable surface is the API and dashboard, backed by PostgreSQL and Redis.
- Worker daemon entrypoints are not yet present as standalone CLI modules in this archive; the compose patch does not invent long-running watcher, validation, processing, delivery, or retry workers.

## Gaps

- `SL-RUN-019` still needs explicit standalone `watcher`, `worker`, and processing service entrypoints once the worker loop CLIs are requirements-backed and implemented.
- A full end-to-end file ingestion smoke test was not added in this patch.

## Rollback

Remove the added Docker files, remove the three added runtime dependencies from `requirements.txt`, and delete this worklog.

## Next Step

Implement requirements-backed worker CLI entrypoints for watcher polling, validation, processing, delivery, and retry scheduling, then extend compose with those services and dedicated health/readiness checks.
