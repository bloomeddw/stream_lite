# WORKLOG-20260607-postgres-check-constraint-collision

## Summary
Fixed first-run PostgreSQL migration failure caused by duplicate generated CHECK constraint names for repeated non-native SQLAlchemy Enum columns in the same table.

## Files changed
- `app/db/migrations/versions/20260430_01_initial_durable_state.py`
- `app/db/models.py`
- `tests/db/test_metadata.py`
- `docs/worklogs/WORKLOG-20260607-postgres-check-constraint-collision.md`

## Requirements traceability
- REQ-001 runtime and deployment: Docker Compose first-run initialization SHALL complete.
- REQ-006 job metadata and state: job state and terminal state fields SHALL remain constrained to documented state values.
- REQ-009 retry and recovery: retry stage fields SHALL remain constrained to documented stage values.
- REQ-014 verification and acceptance: schema defects SHALL be caught by automated verification before runtime.
- REQ-016 data contracts and schema governance: database schema constraints SHALL be stable and migration-safe.

## Root cause
`native_enum=False` SQLAlchemy Enums render as table CHECK constraints. The `jobs` table reused the same `job_state` Enum for both `state` and `terminal_state`, producing two constraints named `ck_jobs_job_state`. PostgreSQL rejects duplicate constraint names within one table. The same collision risk existed for `job_state_history.previous_state/new_state` and `retry_schedules.failed_stage/next_stage`.

## Fix
Created distinct non-native Enum objects with the same allowed value sets but unique constraint names for repeated columns in the same table:

- `job_state` / `terminal_job_state`
- `previous_job_state` / `new_job_state`
- `retry_stage` / `next_retry_stage`

This preserves the documented allowed values while making PostgreSQL DDL names unique.

## Tests
- Added `test_metadata_constraint_names_are_unique_per_table` to catch duplicate generated constraint names.
- Static verification performed in this patch workspace to confirm the known duplicate SQL fragments were removed.

## Assumptions
- The database is disposable or newly initialized during this run, because the failing transaction rolled back before Alembic stamped the revision.
- Constraint names are not part of the external API contract; the allowed values are the contract.

## Gaps
- Docker is unavailable in this execution environment, so `docker compose up --build` could not be run here.

## Rollback
Restore the previous versions of the three changed source/test files. If a partially initialized local Docker volume exists, run `docker compose down -v` only when you explicitly want to discard local database state.

## Next step
Rebuild and rerun `docker compose up --build`.
