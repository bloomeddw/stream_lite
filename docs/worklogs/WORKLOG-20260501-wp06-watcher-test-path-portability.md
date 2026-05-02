# WORKLOG-20260501-wp06-watcher-test-path-portability

## Summary

Adjusted the WP-06 watcher service tests so their temporary filesystem roots are passed to Stream Lite path-policy and repository fixtures as POSIX-style absolute paths. This keeps the tests aligned with Stream Lite container-path semantics on Windows hosts, where `str(tmp_path)` emits backslashes and drive-letter paths that the documented path-safety policy rejects.

## Files changed

- `tests/watcher/test_service.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260501-wp06-watcher-test-path-portability.md`

## Requirements affected

- `SL-FDI-021`
- `SL-FDI-022`
- `SL-FDI-024`
- `SL-SEC-001`
- `SL-SEC-012`
- `SL-LIFE-007`
- `SL-EVT-004`
- `SL-EVT-005`

## Decisions applied

- `DEC-009-uuid-generation-ownership`
- `DEC-010-event-stream-naming`

No new architecture decisions were introduced.

## Tests and verification

Verification completed in the review sandbox:

```bash
python -S tools/contract_lint.py --write-inventory
python -S -m py_compile tests/watcher/test_service.py
```

Full pytest, schema fixture validation, and Sphinx verification still need to be run in the project virtual environment because this sandbox does not have the project dev dependencies available.

## Assumptions

- WP-06 tests must be runnable from a Windows checkout while preserving Stream Lite's documented container-path semantics.
- `Path.as_posix()` is acceptable in tests because the service and path policy both operate on absolute POSIX-style container paths.

## Gaps

- No WP-06 service behavior was changed.
- No new migrations, environment variables, API routes, or Streamlit controls were added.

## Rollback notes

Revert `tests/watcher/test_service.py` to use `str(tmp_path)`-derived paths only if WP-06 tests are guaranteed to run exclusively in a POSIX runtime.

## Next step

Run the full WP-06 verification suite. If every command passes, WP-06 can be marked ready for WP-07 validation/quarantine implementation.
