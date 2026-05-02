# WORKLOG-20260430-pytest-contract-import-path-fix

## Summary

Fixed pytest contract-test collection so tests can import repository-local verification utilities from the top-level `tools/` directory before the project is packaged as an installable Python distribution.

## Files changed

- `stream_lite/.gitignore`
- `stream_lite/tests/conftest.py`
- `stream_lite/tools/__init__.py`
- `stream_lite/docs/implementation/development_environment.md`
- `stream_lite/docs/worklogs/WORKLOG-20260430-pytest-contract-import-path-fix.md`

## Requirements affected

- `SL-DCT-025` API schema parity lint contract
- `SL-DCT-026` event schema parity lint contract
- `SL-DCT-032` artifact schema parity lint contract
- `SL-DCT-033` deep invalid fixture lint contract
- `SL-VER-014` verification evidence and contract test execution

## Decisions applied

- Keep Stream Lite un-packaged until runtime implementation begins.
- Use pytest `conftest.py` to add the repository root to `sys.path` for contract verification tests.
- Add a minimal `tools/__init__.py` so the utilities directory is importable as a Python package during contract tests.

## Tests / verification

Expected local verification command from the repository root:

```powershell
pytest tests/contract
```

This worklog addresses the collection-time error:

```text
ModuleNotFoundError: No module named 'tools'
```

## Assumptions

- Contract tests are run from the repository root.
- The `.venv` directory is local-only and should not be included in future zip patches or source control.

## Gaps

- Runtime package layout is still intentionally deferred until implementation planning and Codex coding begin.
- Full contract test execution should be rerun locally after applying this patch.

## Rollback notes

Remove `tests/conftest.py` and `tools/__init__.py` only after the project has an installable Python package or an equivalent test-path configuration.

## Next step

Apply this patch and rerun:

```powershell
pytest tests/contract
```
