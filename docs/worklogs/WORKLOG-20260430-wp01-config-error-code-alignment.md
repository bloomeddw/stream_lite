# WORKLOG-20260430-wp01-config-error-code-alignment

## Summary
Aligned the WP-01 runtime configuration error-code vocabulary before WP-02. The active requirements now use the same documented and implemented error codes for configuration failures: `CONFIG_MISSING`, `CONFIG_INVALID_ENUM`, and `CONFIG_UNSUPPORTED_DEFERRED_PROFILE`.

## Files Changed
- `docs/reqs/REQ-001-runtime-and-deployment.md`
- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
- `docs/worklogs/WORKLOG-20260430-wp01-config-error-code-alignment.md`

## Requirements Affected
- `SL-RUN-020` - runtime configuration loader contract
- `SL-RUN-002` - API port runtime configuration
- `SL-RUN-003` - dashboard port runtime configuration
- `SL-RUN-007` - runtime environment loading
- `SL-RUN-009` - broker profile selection
- `SL-RUN-010` - processing engine selection
- `SL-REQ-004` - requirements change control

## Decision Applied
The canonical WP-01 configuration error-code vocabulary remains the broader vocabulary already documented in `REQ-001`, `docs/operations/environment_variables.md`, and implemented in `app/config/settings.py`:

- `CONFIG_MISSING` for missing required configuration without a default.
- `CONFIG_INVALID_ENUM` for unsupported enum, range, boolean, or numeric configuration values.
- `CONFIG_UNSUPPORTED_DEFERRED_PROFILE` for explicitly deferred v0.1 profiles such as `flink` or `redpanda`.

No new error codes were introduced. `SL-RUN-020` was updated to match the active docs and implementation rather than changing the implementation or tests.

## Verification Commands and Results
- `python -S tools/contract_lint.py --write-inventory` - passed in this patch environment.
- `python -S -m py_compile $(find app tools tests -name '*.py')` - passed in this patch environment.
- `python tools/validate_schema_examples.py --write-evidence` - not completed in this patch environment because dependency-backed Python execution timed out; the schema contracts and examples were not changed by this patch and should be rerun in the project `.venv` before WP-02.
- `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt` - not completed in this patch environment because dependency-backed Python execution timed out; rerun in the project `.venv` before WP-02.
- `pytest tests/contract` - not completed in this patch environment because dependency-backed Python execution timed out; rerun in the project `.venv` before WP-02.
- `pytest tests/config tests/api tests/observability` - not completed in this patch environment because dependency-backed Python execution timed out; rerun in the project `.venv` before WP-02.

## Assumptions
- WP-01 should keep the implemented and documented error-code vocabulary stable unless a later requirement change explicitly adds a more granular taxonomy.
- Integer range and boolean parsing failures are treated as `CONFIG_INVALID_ENUM` for v0.1 local-demo operator simplicity.

## Gaps
- None known for WP-01 configuration error-code alignment.

## Rollback Notes
To roll back this patch, restore the previous `SL-RUN-020` row in `REQ-001`. If rolled back, the conflict between `SL-RUN-020`, environment variable docs, tests, and implementation will return and should block WP-02.

## Next Step
Start WP-02 Pydantic Models and Schema Binding after confirming the repo snapshot excludes generated/cache artifacts.
