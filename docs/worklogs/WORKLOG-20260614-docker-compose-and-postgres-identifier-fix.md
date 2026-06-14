# 2026-06-14 Docker Compose Image Build and PostgreSQL Identifier Fix

## Summary

Fixed two startup blockers found during Docker Compose execution:

1. The `dashboard` service referenced `stream_lite_app:local` without declaring a build context, so a clean machine could attempt to use a missing local image.
2. The first Alembic migration used PostgreSQL identifiers longer than the PostgreSQL 63-byte identifier limit, causing migration startup to fail while creating later durable-state tables.

The patch keeps the host PostgreSQL port at `5600` while preserving the correct in-container connection contract of `postgres:5432`.

## Files Changed

- `docker-compose.yml`
- `.env.example`
- `app/db/migrations/versions/20260430_01_initial_durable_state.py`
- `app/db/models.py`
- `docs/operations/environment_variables.md`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260614-docker-compose-and-postgres-identifier-fix.md`

## Requirements Addressed

- `SL-RUN-001` — compose shall start required services with one command.
- `SL-RUN-004` — PostgreSQL shall persist data through a named Docker volume.
- `SL-RUN-005` — Redis shall use named persisted broker data.
- `SL-RUN-007` — runtime configuration shall be supplied through environment variables.
- `SL-RUN-014` — `.env.example` values shall be sufficient for default demo startup.
- `SL-RUN-021` — runtime docs shall identify named volumes and bind/port surfaces.
- `SL-DATA-001` / WP-03 durable-state migration intent — database schema shall initialize on PostgreSQL.

## Decisions

- `POSTGRES_PORT=5600` is a host-side Docker Compose port only; containers still use `postgres:5432`.
- `REDIS_PORT` was added to `.env.example` and operations docs because compose already exposes it as a host-side override.
- The shared app image tag remains `stream_lite_app:local`, but each app service now declares the same build context through a compose YAML anchor so clean builds do not depend on an image preexisting locally.
- Overlong database identifiers were shortened without changing columns or uniqueness/index semantics:
  - `uq_delivery_attempts_job_id_destination_folder_id_attempt_number` -> `uq_delivery_attempts_job_dest_attempt`
  - `ix_duplicate_suppression_observations_existing_job_id_observed_at` -> `ix_dup_obs_existing_job_observed_at`

## Tests and Verification

Performed static verification in this environment:

- Parsed `docker-compose.yml` with PyYAML and confirmed `migrate`, `api`, and `dashboard` each declare `build.context: .` and image `stream_lite_app:local`.
- Confirmed PostgreSQL host mapping remains `${POSTGRES_PORT:-5600}:5432`.
- Scanned migration/model constraint and index identifiers and found no `name=`, `op.create_index`, `op.drop_index`, or `sa.Index` identifiers over 63 characters in the touched database files.
- Confirmed `.env.example` includes the compose-only host port mappings now referenced by `docker-compose.yml`.

## Assumptions

- The user has another PostgreSQL service bound to host port `5432`, so Stream Lite must keep using host port `5600`.
- Stream Lite containers use the compose network and therefore connect to the Postgres service on its container port `5432`.
- No production data exists in the local Stream Lite Docker volume unless the operator explicitly needs to preserve it.

## Gaps

- Docker is unavailable in this execution environment, so `docker compose up --build` could not be run here.
- If an older failed migration left partial state despite transactional DDL, the local Stream Lite volume may still need to be reset with `docker compose down -v` before rerunning the first initialization.

## Rollback

Restore the previous versions of the changed files. If a local test volume was reset during troubleshooting, data in that local volume cannot be recovered from this patch.

## Next Step

Apply the patch, run `docker compose config` to confirm the rendered services, then run `docker compose up --build`. If migration still fails, capture the new `migrate` log from the first stack run after applying this patch.
