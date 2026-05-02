# WORKLOG-20260430-codex-task-guide-batch-4

## Summary

Created the Batch 4 Codex-oriented implementation task guide and verification wiring requested by the user. This patch keeps implementation deferred while converting existing requirements/contracts into ordered coding packages with traceability, tests, evidence, and rollback notes.

## Files Changed

- `requirements-dev.txt`
- `docs/index.rst`
- `docs/sphinx_build.md`
- `docs/implementation/README.md`
- `docs/implementation/CODEX_TASK_GUIDE.md`
- `docs/implementation/naming_review.md`
- `docs/verification/evidence/README.md`
- `docs/worklogs/BATCH_PROGRESS-20260426-contract-hardening.md`
- `docs/worklogs/WORKLOG-20260430-codex-task-guide-batch-4.md`
- `tools/validate_schema_examples.py`
- `tools/verify_sphinx_build.py`
- `tests/contract/test_schema_examples.py`
- `tests/contract/test_sphinx_build_command.py`

## Requirements Affected

- SL-DECOMP-009
- SL-REQ-004
- SL-DCT-022
- SL-DCT-024
- SL-DCT-025
- SL-DCT-026
- SL-DCT-027
- SL-DCT-028
- SL-VER-027
- SL-VER-028
- SL-VER-031
- V-SL-SPHINX-001

## Decisions Applied

- `DEC-009-uuid-generation-ownership.md`: Codex work packages use application-owned UUID generation before insert.
- Duration metrics remain standardized on seconds.
- Streamlit remains API-backed and does not write directly to the database in MVP.

## Tests and Verification

Ran:

```bash
python -S tools/contract_lint.py --write-inventory
```

Result:

```text
contract_lint passed
```

Development dependency tests were wired but not run because this container does not have `jsonschema`, `pytest`, or `sphinx` installed. The commands to run after installing development dependencies are documented in `docs/sphinx_build.md` and `docs/worklogs/BATCH_PROGRESS-20260426-contract-hardening.md`.

## Assumptions

- Codex will run inside an environment where development dependencies can be installed from `requirements-dev.txt`.
- The task guide is a coding guide, not an implementation plan approval to start runtime code.
- Future runtime modules should follow the naming map unless the user approves a design decision changing the module layout.

## Gaps

- Executable JSON Schema validation has not yet been run in this container.
- Sphinx verifier was run and produced skipped evidence because `sphinx-build` is not installed; a full HTML build still needs dependencies installed.
- Runtime implementation remains intentionally deferred.

## Rollback Notes

Rollback by removing the files listed above and restoring `docs/index.rst`, `docs/sphinx_build.md`, and `docs/worklogs/BATCH_PROGRESS-20260426-contract-hardening.md` to the previous version. No database, runtime, or generated application state exists in this patch.

## Next Step

Install development dependencies and execute Batch 5 verification commands before allowing runtime implementation work packages to start.
