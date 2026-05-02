# WORKLOG-20260501-wp05-prep-fastapi-control-plane-map

## Summary

Added a documentation-only WP-05 FastAPI control-plane implementation map and a ready-to-use Codex prompt to reduce reasoning burden before WP-04 starts. This patch does not implement WP-04 or WP-05 runtime code.

## Files Changed

- `docs/implementation/WP05_FASTAPI_CONTROL_PLANE_MAP.md`
- `docs/implementation/WP05_CODEX_PROMPT.md`
- `docs/implementation/README.md`
- `docs/implementation/CODEX_TASK_GUIDE.md`
- `docs/index.rst`
- `docs/worklogs/INDEX.md`
- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
- `docs/verification/evidence/sphinx_build.txt`
- `docs/worklogs/WORKLOG-20260501-wp05-prep-fastapi-control-plane-map.md`

## Requirements Affected

- `SL-API-001` through `SL-API-050`
- `SL-OBS-001` through `SL-OBS-012`
- `SL-SEC-001` through `SL-SEC-017`
- `SL-FWM-020` through `SL-FWM-039`
- `SL-EVT-015`
- `SL-LIFE-015`
- `SL-RET-012`

The patch adds planning traceability only; it does not close implementation verification for those requirements.

## Decisions Applied

- WP-05 remains blocked until WP-04 is complete and verified.
- API event listing shall use persisted event metadata or WP-04 safe listing primitives and shall not read Redis Streams directly.
- Mutation command routes shall persist command intent before returning `202`.
- No new environment variables are needed for WP-05 planning.

## Verification

Commands run:

```bash
python3 -S tools/contract_lint.py --write-inventory
python3 -S tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
```

Results:

- `contract_lint passed`
- Sphinx verifier recorded an accepted skip because `sphinx-build` was not installed in this container.

Dependency-backed pytest and schema validation were not rerun in this container because this is a docs-only planning patch and the local project `.venv` should be used for dependency-backed checks after applying the patch.

## Assumptions

- WP-04 will add the event outbox, Redis Streams wrapper, dispatcher primitives, dead-letter handling, and event listing support before WP-05 begins.
- WP-05 will use the route map in `docs/implementation/WP05_FASTAPI_CONTROL_PLANE_MAP.md` unless a requirements-backed contradiction is found.

## Gaps

- WP-05 is not implemented.
- WP-04 is not implemented by this patch.
- The WP-05 prompt should be used only after WP-04 completion evidence is present.

## Rollback Notes

Revert the added WP-05 planning files and the index updates. No runtime code, database state, or generated migration state is affected.

## Next Step

Proceed with WP-04 using the existing WP-04 prompt. After WP-04 passes, use `docs/implementation/WP05_CODEX_PROMPT.md` to start WP-05 with reduced reasoning burden.
