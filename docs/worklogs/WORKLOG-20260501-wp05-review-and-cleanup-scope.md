# WORKLOG-20260501-wp05-review-and-cleanup-scope

## Summary

Reviewed WP-05 after Codex implementation against the requirements, WP-05 prompt/reference maps, API endpoint contracts, worklogs, and `rtc_source.md`. WP-05 is functionally close but not cleanly closed. This patch applies documentation cleanup for moved WP-05 reference paths and records the remaining cleanup scope in `docs/implementation/WP05_REVIEW_FINDINGS.md`.

No runtime code was changed. WP-06 was not started.

## Files changed

- `docs/index.rst`
- `docs/implementation/README.md`
- `docs/implementation/CODEX_TASK_GUIDE.md`
- `docs/implementation/WP05_CODEX_PROMPT.md`
- `docs/implementation/WP05_REVIEW_FINDINGS.md`
- `docs/implementation/wp_reference/WP05_FASTAPI_CONTROL_PLANE_MAP.md`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260501-wp05-review-and-cleanup-scope.md`

## Requirements affected

- `SL-API-001` through `SL-API-050`
- `SL-OBS-001` through `SL-OBS-012` where route logs/metrics are required
- `SL-SEC-001` through `SL-SEC-017` where path safety is touched by API routes
- `SL-LIFE-015` for command status visibility
- `SL-RET-012` for manual retry command acceptance
- Sphinx verification requirements in `REQ-014`

## Decisions applied

- WP-05 reference files are currently located under `docs/implementation/wp_reference/`; docs and prompt references must use that checked-in path unless the files are moved back to the implementation root.
- Cleanup findings are documented as review evidence, not silently corrected in runtime code.
- WP-06 remains blocked until WP-05 cleanup is resolved or explicit requirements-backed deferrals are committed.

## Tests and verification

Commands attempted in this sandbox:

```bash
python -S tools/contract_lint.py --write-inventory
```

Result:

- `contract_lint passed`

Dependency-backed commands were not rerun successfully in this sandbox because normal `/opt/pyvenv/bin/python` startup hangs on site-package import, while `/usr/bin/python3` does not include all project dependencies. The cleanup prompt requires rerunning the full verification suite in the project virtual environment.

Static checks performed:

- Confirmed no `__pycache__`, `.pytest_cache`, `.tmp`, `tmp`, `.venv`, `wheelhouse`, or `*.pyc` artifacts were present in the uploaded repository snapshot.
- Confirmed `docs/index.rst` referenced missing WP-05 files before this patch.
- Confirmed API route code is present but does not yet implement the documented route observability contract broadly.

## Assumptions

- The Codex-reported WP-05 pytest/Sphinx results in `WORKLOG-20260501-wp05-fastapi-control-plane-routes.md` were produced in the user's local virtual environment and need to be rerun after cleanup.
- The WP-05 reference docs were intentionally moved under `docs/implementation/wp_reference/` during the post-WP-05 reference-map patch.

## Gaps

- Runtime cleanup is still required for the findings listed in `docs/implementation/WP05_REVIEW_FINDINGS.md`.
- This patch does not add route metrics/logging middleware, dependency-health `error_code` support, idempotency payload-mismatch checks, or lifecycle-state contract changes.

## Rollback notes

Revert the files listed above. No database, Redis, filesystem, migration, or generated evidence cleanup is required because this patch is documentation-only.

## Next step

Run the WP-05 cleanup prompt against the repository, rerun full verification in the project virtual environment, and only then start WP-06 using `docs/implementation/wp_reference/WP06_WATCHER_REFERENCE.md`.
