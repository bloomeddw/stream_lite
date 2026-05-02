# WORKLOG — WP-07 Migration Copied Size Fix

**Date:** 2026-05-02  
**Scope:** WP-07 validation/quarantine migration repair  
**Status:** Patch prepared

## Summary

Fixed the WP-07 quarantine copied-size migration failure where a fresh Alembic upgrade attempted to add `quarantine_records.copied_size_bytes` after the initial durable-state migration had already created that column.

## Files changed

- `app/db/migrations/versions/20260430_01_initial_durable_state.py`
- `app/db/migrations/versions/20260502_01_add_quarantine_copied_size_bytes.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260502-wp07-migration-copied-size-fix.md`

## Requirements affected

- `REQ-004` — file validation and quarantine
- `REQ-006` — job metadata and state
- `REQ-014` — verification and acceptance

## Implementation notes

- Removed the WP-07 `copied_size_bytes` column from the initial WP-03 durable-state migration so the later WP-07 migration owns that schema evolution.
- Made the WP-07 migration column-aware so in-flight development databases that already have `copied_size_bytes` do not fail with a duplicate-column error.
- Kept downgrade behavior column-aware.

## Tests / verification

Recommended rerun after applying this patch:

```powershell
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/db
pytest tests/validation -q
pytest tests
```

Local patch verification was limited to syntax checks and contract lint in the review sandbox.

## Assumptions

- `copied_size_bytes` is a WP-07 schema addition and should be introduced by the WP-07 migration, not by the original WP-03 migration.
- No destructive cleanup command is required or permitted.

## Gaps

- Full pytest/Sphinx verification should be rerun in the project virtual environment.

## Rollback notes

Reverting this patch restores the duplicate-column failure on fresh migration upgrades when both the initial migration and WP-07 migration define `copied_size_bytes`.

## Next step

Apply the patch and rerun the full verification suite. If all tests pass, WP-07 can proceed toward WP-08 planning.
