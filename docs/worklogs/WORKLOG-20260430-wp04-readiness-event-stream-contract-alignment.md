# WORKLOG-20260430-wp04-readiness-event-stream-contract-alignment

## Summary

Aligned the event stream naming contract before WP-04. `REQ-005` now states that v0.1 lifecycle events publish to `stream_lite.lifecycle` and dead-letter records publish to `stream_lite.dead_letter`. The older split streams `stream_lite.jobs`, `stream_lite.files`, `stream_lite.delivery`, and `stream_lite.commands` are deferred future scope unless a later accepted decision updates the related requirements, schemas, API contracts, examples, consumers, operations docs, and tests together.

WP-04 was not started. No Redis publisher logic, event dispatcher runtime logic, FastAPI routes, watchers, validators, processors, delivery workers, retry schedulers, Streamlit pages, or new migrations were created.

## Files changed

- `docs/reqs/REQ-005-event-streaming.md`
- `docs/design/DEC-010-event-stream-naming.md`
- `docs/design/INDEX.md`
- `.gitignore`
- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
- `docs/verification/evidence/sphinx_build.txt`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260430-wp04-readiness-event-stream-contract-alignment.md`

## Requirements affected

- `SL-EVT-006`
- `SL-EVT-012`
- `SL-EVT-013`
- `SL-EVT-014`
- `SL-EVT-016`
- `SL-EVT-024`
- `SL-EVT-025`
- `SL-EVT-026`

## Decision applied

- Added `DEC-010: Event Stream Naming`.
- Accepted the v0.1 stream topology of `stream_lite.lifecycle` for active lifecycle events and `stream_lite.dead_letter` for dead-letter records.
- Deferred domain-specific streams until a future decision activates stream partitioning and updates the event schema inventory, API model, examples, stream offsets, operations docs, consumers, and tests together.

## Verification commands/results

```bash
python3 -S tools/contract_lint.py --write-inventory
python3 -S tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
python3 -S -m py_compile $(find app tools tests -name '*.py')
```

Results:

- `python3 -S tools/contract_lint.py --write-inventory`: passed.
- `python3 -S tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`: completed with the accepted skipped status because `sphinx-build` was not available in this container; `docs/verification/evidence/sphinx_build.txt` was updated with skip evidence.
- `python3 -S -m py_compile $(find app tools tests -name '*.py')`: passed.

Dependency-backed verification commands were not rerun in this container because normal site-package imports time out in this environment. The Stream Lite `.venv` should rerun these unchanged commands after applying the patch:

```powershell
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/contract
pytest tests/config tests/api tests/observability
pytest tests/schemas
pytest tests/db tests/repositories
```

Evidence artifacts updated in this patch:

- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
- `docs/verification/evidence/sphinx_build.txt`

## Assumptions

- `docs/schemas/events.md`, `schemas/examples/events/*`, and `app/api/schemas/api_models.py` already represented the active v0.1 lifecycle stream as `stream_lite.lifecycle`.
- WP-04 will implement Redis publication against the resolved v0.1 contract rather than reintroducing domain-specific stream routing.
- Domain-specific streams remain useful future scope but are not required for the local-demo MVP.

## Gaps

- No known contract gap remains for WP-04 stream naming after this patch.
- Dependency-backed validation and pytest commands still need local `.venv` confirmation after applying the patch because this container cannot reliably import installed third-party packages.

## Rollback notes

- Revert `docs/reqs/REQ-005-event-streaming.md`, `docs/design/DEC-010-event-stream-naming.md`, `docs/design/INDEX.md`, `.gitignore`, updated evidence files, `docs/worklogs/INDEX.md`, and this worklog to return to the WP-03 baseline.
- If rollback reintroduces the old domain-stream text, WP-04 must not start until stream naming is reconciled again with `docs/schemas/events.md` and `app/api/schemas/api_models.py`.

## Next step

- Apply the patch locally, rerun the full `.venv` verification suite, and start WP-04 only after the verification suite passes and no generated/cache/vendor artifacts remain.
