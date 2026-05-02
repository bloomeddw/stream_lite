# WORKLOG-20260501-wp04-review-wp05-prompt-hardening

## Summary

Reviewed the WP-04 Codex output for scope, stream naming alignment, and follow-on readiness. Found one remaining test-contract mismatch: an older repository test still inserted an outbox row with the deferred stream name `stream_lite.jobs`. Updated the test to use the active lifecycle stream constant so tests no longer exercise deferred domain-stream topology before a future stream-partitioning decision.

Also hardened the WP-05 implementation guidance to reduce Codex reasoning burden before FastAPI route work begins. Added a low-reasoning checklist with fixed environment setup, implementation order, module map, route response rules, repository-use map, required tests, and stop conditions. Updated the WP-05 Codex prompt to explicitly use the existing `.venv` in `C:\Users\asosa\stream_lite` and to avoid vendored dependency folders.

No WP-05 runtime implementation was started.

## Files changed

- `tests/repositories/test_events.py`
- `docs/implementation/WP05_FASTAPI_CONTROL_PLANE_MAP.md`
- `docs/implementation/WP05_CODEX_PROMPT.md`
- `docs/implementation/WP05_LOW_REASONING_CHECKLIST.md`
- `docs/implementation/README.md`
- `docs/index.rst`
- `docs/worklogs/WORKLOG-20260501-wp04-review-wp05-prompt-hardening.md`
- `docs/worklogs/INDEX.md`

## Requirements affected

- Event stream alignment from the WP-04 readiness decision remains applied: lifecycle event publication uses `stream_lite.lifecycle`; deferred domain streams remain future scope.
- WP-05 preparation remains documentation-only and does not implement API behavior.

## Decisions applied

- Repository tests that need an outbox stream name shall use the active `LIFECYCLE_STREAM_NAME` constant instead of hard-coded deferred stream names.
- WP-05 Codex work shall use the existing repository virtual environment instead of user-site packages or temporary vendored dependency folders.
- WP-05 route implementation shall follow `WP05_LOW_REASONING_CHECKLIST.md` to avoid re-deriving route ordering, error mapping, and repository-use rules from multiple docs.

## Verification commands/results

Static review performed in this patch:

- Confirmed no WP-05 runtime code was added.
- Confirmed the prior hard-coded `stream_lite.jobs` test reference was replaced with the active lifecycle stream constant.
- Confirmed the WP-05 prompt now instructs Codex to activate `.venv` and not create `.pytest_vendor/`, `pytest_vendor/`, or `wheelhouse/`.

Dependency-backed verification should be run locally after applying this patch:

```powershell
cd C:\Users\asosa\stream_lite
.\.venv\Scripts\Activate.ps1
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/contract
pytest tests/config tests/api tests/observability
pytest tests/schemas
pytest tests/db tests/repositories
pytest tests/events
```

## Assumptions

- The existing WP-04 implementation is otherwise accepted and functionally verified by its worklog and evidence.
- The stale deferred stream name in `tests/repositories/test_events.py` was an oversight from WP-03-era repository tests, not a new WP-04 stream-routing requirement.
- The repository already contains a working `.venv` for local dependency-backed commands.

## Gaps

- No known WP-04 implementation gap remains after the stream-name test cleanup.
- WP-05 has not been implemented; the new checklist only reduces reasoning burden for the next Codex prompt.

## Rollback notes

- Revert this patch to restore the previous WP-05 prompt docs and the older hard-coded repository test stream name.
- If rolled back, do not start WP-05 until the deferred stream name in the repository test is reconciled again with `DEC-010` and `REQ-005`.

## Next step

- Apply this patch, rerun the local `.venv` verification suite, then start WP-05 using `docs/implementation/WP05_CODEX_PROMPT.md`.
