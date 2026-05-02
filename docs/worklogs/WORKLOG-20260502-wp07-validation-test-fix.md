# WORKLOG-20260502-wp07-validation-test-fix

## Summary
Fixed two WP-07 validation test failures reported after the WP-07 review/safety alignment patch.

## Files Changed
- `app/validation/validator.py`
- `tests/validation/test_quarantine.py`
- `docs/worklogs/WORKLOG-20260502-wp07-validation-test-fix.md`
- `docs/worklogs/INDEX.md`

## Requirements Affected
- `REQ-004` validation/quarantine behavior
- `REQ-013` path safety and host path avoidance
- `REQ-014` verification and acceptance
- `REQ-016` schema/artifact governance

## Implementation Notes
- Custom validator allowlist extensions now pass the extension gate and receive a safe UTF-8 decodability check when no explicit structured parser exists for that extension.
- The quarantine copy-size test now writes deterministic LF bytes on Windows so copied byte counts are measured against exact source bytes, not platform newline translation.
- The production quarantine copy behavior remains byte-preserving.

## Tests / Verification
Local sandbox verification:
- `python -m py_compile app/validation/validator.py tests/validation/test_quarantine.py tests/validation/test_validator.py` passed.

The sandbox does not have project dependencies such as SQLAlchemy installed, so full pytest verification must be rerun in the project virtual environment.

Required rerun:
- `python -S tools/contract_lint.py --write-inventory`
- `python tools/validate_schema_examples.py --write-evidence`
- `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`
- `pytest tests/validation -q`
- `pytest tests`

## Assumptions
- A custom allowed extension without a WP-07 structured parser should be accepted when the file is UTF-8 decodable and non-empty.
- `copied_size_bytes` should represent copied file bytes exactly, so tests should create deterministic bytes on all platforms.

## Gaps
- None known after the targeted fixes; full project verification is required in the user environment.

## Rollback Notes
Revert this patch to restore the prior strict parser-only custom extension behavior and the previous text-mode quarantine test fixture.

## Next Step
Rerun WP-07 verification. If all tests pass, continue to WP-08.
