# WORKLOG-20260501-wp05-health-test-fixture-fix

## Summary

Reviewed the WP-05 cleanup verification results and fixed the remaining failing API test. The failure was in the test harness, not the dependency-health route implementation: `build_test_app()` always auto-created the configured filesystem roots even when a caller supplied an explicit `FakeFilesystemReader`, which prevented `test_dependency_health_filesystem_root_includes_error_code` from simulating a missing output root.

The helper now auto-seeds default filesystem roots only when no custom fake filesystem is provided. Tests that need a specific filesystem state can now supply that state directly, and tests that do not care about filesystem availability still receive the default ready roots.

## Files changed

- `tests/api/test_app_factory.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260501-wp05-health-test-fixture-fix.md`

## Requirements affected

- `SL-API-013` dependency-health readiness semantics.
- `SL-API-014` dependency-health unavailable response behavior.
- `SL-API-041` documented API verification coverage.
- `SL-OBS-005` route observability evidence remains covered by the previously passing route-observability tests.

## Decisions applied

No new design decision was introduced. This is a test-harness correction that preserves the WP-05 cleanup contract: explicit test fixtures must be able to model unavailable dependency roots without production-code changes or new environment variables.

## Tests and verification

User-provided verification results before this patch showed:

- `python -S tools/contract_lint.py --write-inventory`: passed.
- `python tools/validate_schema_examples.py --write-evidence`: 169 examples passed, 0 failed.
- `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`: Sphinx exit code 0.
- `pytest tests/contract`: 3 passed.
- `pytest tests/schemas`: 213 passed.
- `pytest tests/db tests/repositories`: 9 passed.
- `pytest tests/events`: 8 passed.
- `pytest tests/config tests/api tests/observability`: 54 passed, 1 failed.
- `pytest tests/api`: 40 passed, 1 failed.

The only failing check was `tests/api/test_health_routes.py::test_dependency_health_filesystem_root_includes_error_code`, where the expected status was `503` but the helper-created filesystem roots caused `/health/dependencies` to return `200`.

Sandbox verification after this patch:

```bash
python -m py_compile tests/api/test_app_factory.py
python -S tools/contract_lint.py --write-inventory
```

Result: both commands passed in the review sandbox.

Full pytest, schema example validation, and Sphinx verification still need to be rerun in the project virtual environment because the review sandbox does not include the project development dependencies.

## Assumptions

- Existing tests that pass a custom `FakeFilesystemReader` already declare the roots they require.
- Existing tests that call `build_test_app()` without a custom filesystem reader should continue receiving default ready roots.
- The dependency-health implementation from the previous WP-05 cleanup follow-up patch is correct once the test fixture stops masking unavailable filesystem roots.

## Gaps

- The full WP-05 verification suite must be rerun in the developer environment after applying this patch.
- `docs/_build/` should be removed before any final handoff zip if Codex rebuilds Sphinx locally.

## Rollback notes

Revert `tests/api/test_app_factory.py` to restore the previous auto-seeding behavior. That rollback would reintroduce the inability to test missing filesystem roots through an explicit fake filesystem fixture.

## Next step

Apply this patch and rerun the full WP-05 verification suite. If all commands pass, WP-05 can be marked ready for WP-06. Start WP-06 only from `docs/implementation/wp_reference/WP06_WATCHER_REFERENCE.md` and the implementation guide after WP-05 is verified clean.
