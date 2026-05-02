# WORKLOG-20260501-wp06-host-path-resolver-fix

## Summary

Fixed the WP-06 watcher service test portability failure reported from the Windows verification run. The failing tests passed Windows temporary paths into `PathPolicy`, which correctly rejects drive-letter paths because Stream Lite path contracts use absolute POSIX-style container paths. The fix keeps watcher source and destination records in container-path form while allowing the test harness to resolve those container paths to host temporary directories for filesystem scanning.

## Files changed

- `app/watcher/service.py`
- `tests/watcher/test_service.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260501-wp06-host-path-resolver-fix.md`

## Requirements affected

- REQ-002: folder watch management and route configuration remains container-path based.
- REQ-003: watcher polling continues to scan stable source files without mutating source content.
- REQ-006: file and job metadata continue to persist safe display paths and container locators.
- REQ-012: watcher logs continue to use safe display paths.
- REQ-013: path validation remains strict and continues to reject Windows drive-letter paths at contract boundaries.

## Decisions applied

- Preserved POSIX-style container paths as the repository and path-policy contract.
- Added an injectable filesystem resolver to `WatcherService` for host-mounted test or runtime contexts where a validated container path must be mapped to a local filesystem path for scanning.
- Kept the default resolver as identity so Docker/container execution remains unchanged.

## Tests and verification

Performed in this review sandbox:

```bash
python -S -m py_compile app/watcher/*.py tests/watcher/*.py
```

Result: passed.

The attached user verification output showed that contract lint, schema example validation, Sphinx build, and non-watcher suites passed before this patch, with the remaining failure isolated to `tests/watcher/test_service.py` path-policy setup.

## Assumptions

- WP-06 watcher records should store container paths, not host-only paths.
- Host path mapping is a test/runtime integration concern and does not require a new environment variable.

## Gaps

- Full pytest and Sphinx verification must be rerun in the project virtual environment after applying this patch.

## Rollback notes

To roll back, remove the filesystem resolver injection from `WatcherService`, restore `tests/watcher/test_service.py` to use direct `tmp_path` values as path-policy roots, and remove this worklog/index entry. That rollback would reintroduce Windows path-policy failures.

## Next step

Apply the patch and rerun the full WP-06 verification suite. If all commands pass, WP-06 is ready for WP-07 validation/quarantine work.
