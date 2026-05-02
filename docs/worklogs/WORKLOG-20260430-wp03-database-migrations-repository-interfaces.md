# WORKLOG-20260430-wp03-database-migrations-repository-interfaces

## Summary

Implemented WP-03 only: SQLAlchemy 2.x durable-table models, session primitives, Alembic scaffolding, an initial durable-state migration, and persistence-only repository surfaces for the documented durable tables. WP-04 was not started. UUIDs remain application-owned per `DEC-009`, `STREAM_LITE_DATABASE_URL` was reused without adding new env vars, Alembic migrations and SQLAlchemy models were added for the documented durable tables, and repository methods remain persistence primitives only rather than business workflow implementations.

## Files changed

- Persistence dependencies and configuration:
  - `requirements.txt`
  - `alembic.ini`
- Database scaffold and models:
  - `app/db/__init__.py`
  - `app/db/base.py`
  - `app/db/session.py`
  - `app/db/models.py`
  - `app/db/migrations/env.py`
  - `app/db/migrations/script.py.mako`
  - `app/db/migrations/versions/20260430_01_initial_durable_state.py`
- Repository surfaces:
  - `app/repositories/__init__.py`
  - `app/repositories/base.py`
  - `app/repositories/watchers.py`
  - `app/repositories/files.py`
  - `app/repositories/jobs.py`
  - `app/repositories/validation.py`
  - `app/repositories/processing.py`
  - `app/repositories/delivery.py`
  - `app/repositories/retry.py`
  - `app/repositories/commands.py`
  - `app/repositories/stage_claims.py`
  - `app/repositories/events.py`
  - `app/repositories/observability.py`
- Verification:
  - `tests/conftest.py`
  - `tests/db/test_metadata.py`
  - `tests/db/test_migrations.py`
  - `tests/repositories/test_commands.py`
  - `tests/repositories/test_events.py`
  - `tests/repositories/test_imports.py`
  - `tests/repositories/test_jobs.py`
  - `tests/repositories/test_stage_claims.py`
- Worklog docs:
  - `docs/worklogs/INDEX.md`
  - `docs/worklogs/WORKLOG-20260430-wp03-database-migrations-repository-interfaces.md`

## Requirements affected

- `SL-JOB-001` through `SL-JOB-051`
- `SL-LIFE-009`
- `SL-LIFE-015`
- `SL-LIFE-017`
- `SL-EVT-011`
- `SL-EVT-015`
- `SL-VAL-016`
- `SL-RET-006`
- `SL-RET-012`
- `SL-DCT-018`
- `SL-RUN-004`
- Related repository traceability rows in `docs/data/migration_plan.md`

## Contract/schema usage

- `docs/data/logical_model.md` and `docs/data/migration_plan.md` defined the durable table inventory, ownership, and migration conventions.
- `docs/reqs/REQ-006-job-metadata-and-state.md`, `REQ-017-end-to-end-lifecycle-and-handoff-orchestration.md`, `REQ-005-event-streaming.md`, `REQ-009-retry-and-recovery.md`, `REQ-012-operational-logging-and-observability.md`, and `REQ-004-file-validation-and-quarantine.md` defined repository-facing persistence fields and invariants.
- `schemas/events/*.schema.json` remained authoritative for event envelope fields referenced by `event_outbox`.
- `schemas/artifacts/output_manifest.schema.json` and `schemas/artifacts/quarantine_record.schema.json` remained authoritative for persisted artifact-facing fields.
- `STREAM_LITE_DATABASE_URL` from `.env.example`, `docs/operations/environment_variables.md`, and `app/config/settings.py` was reused without adding new environment variables.

## Decisions applied

- Keep application-owned UUID generation on the Python side only. No database UUID defaults were added for durable application identifiers.
- Use Alembic for migration scaffolding and include a downgrade path in the initial migration.
- Keep repository methods business-neutral: create/get/list/update persistence primitives only, with transaction-safe state/history and outbox helpers where the requirement explicitly couples those records.
- Use SQLite-compatible local tests while preserving PostgreSQL-oriented migration intent through SQLAlchemy type variants.
  Route-tag list columns use a SQLite JSON representation for local tests and a PostgreSQL `text[]` variant for the PostgreSQL target.
  JSON payload columns use SQLite JSON locally and PostgreSQL `jsonb` variants for the PostgreSQL target.
- Resolve repository naming in favor of the accepted WP-03 surface while keeping implementation compact.
  `app/repositories/observability.py` contains both `OperationalLogRepository` and `HealthRepository` because `docs/data/repository_contracts.md` is absent and the task instructions named `observability.py` explicitly.
- Resolve documented contract mismatches conservatively:
  - `event_outbox` uses `outbox_id` as the primary key and `event_id` as a unique application-owned event identifier because the repo docs and `SL-DCT-018` document `outbox_id`, even though the work-package prompt simplified the table shape.
  - `watcher_sources` and `watcher_destinations` use `source_folder_id` and `destination_folder_id` because those names are the active requirement and logical-model contract, even though the work-package prompt used shorter aliases.
  - `idempotency_keys` uses unique scope plus key because `docs/data/migration_plan.md` documents scoped uniqueness; local tests verify duplicate rejection for the same scope and key.

## Verification commands/results

```powershell
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/contract
pytest tests/config tests/api tests/observability
pytest tests/schemas
pytest tests/db tests/repositories
```

Results:

- `python -S tools/contract_lint.py --write-inventory`: passed.
- `python tools/validate_schema_examples.py --write-evidence`: passed with `169` examples validated, `169` passed, and `0` failed.
- `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`: completed with the accepted skipped status because `sphinx-build` was not available as an executable in this host environment; `docs/verification/evidence/sphinx_build.txt` was updated with the skip evidence.
- `pytest tests/contract`: passed with `3 passed`.
- `pytest tests/config tests/api tests/observability`: passed with `16 passed`.
- `pytest tests/schemas`: passed with `213 passed`.
- `pytest tests/db tests/repositories`: passed with `9 passed`.

Evidence artifacts kept current:

- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
- `docs/verification/evidence/schema_fixture_validation.md`
- `docs/verification/evidence/sphinx_build.txt`

## Assumptions

- The workspace snapshot is a filesystem export rather than a live Git checkout, so hygiene checks rely on direct filesystem inspection.
- Local verification uses an external temporary dependency directory because the host Python environment has a conflicting `PYTHONPATH` setting and the repository must not retain temporary vendor artifacts.
- SQLite is acceptable for local repository and migration smoke tests as long as PostgreSQL-targeted types and differences are documented.

## Gaps

- No known WP-03 functional gaps remain after verification.
- SQLite local verification does not prove PostgreSQL-only runtime behavior such as native `jsonb` storage or native array semantics; SQLAlchemy type variants were used so the migration and model intent still tracks the documented PostgreSQL MVP target.

## Rollback notes

- Revert the WP-03 persistence files, repository modules, new tests, dependency declaration changes, worklog index entry, and this worklog to return to the WP-02 state.
- If rollback follows a live database migration run, execute the Alembic downgrade for revision `20260430_01` or drop/reset the demo database volume before re-running later work packages.
- Remove generated verification artifacts again after rollback if they are re-created during reversal testing.

## Next step

- Hand off WP-03 as ready for WP-04 planning or implementation without starting WP-04 in this patch set.
