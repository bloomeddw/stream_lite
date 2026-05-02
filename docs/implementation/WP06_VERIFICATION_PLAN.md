# WP-06 Verification Plan: Watcher Routing, Detection, Stability, Deduplication, and Registration

## Purpose

This plan lists the verification commands and expected evidence for WP-06 after the watcher implementation is complete. It is a documentation-only checklist, not a Codex prompt.

WP-06 starts only after WP-05 has passed the full verification suite. WP-06 must use `docs/implementation/wp_reference/WP06_WATCHER_REFERENCE.md` as the implementation map.

## Scope under verification

WP-06 verification covers watcher-side orchestration only:

- route-tag normalization and `tag_match_all_destinations` matching
- route preview results for matched and unmatched source/destination folders
- direct source-folder scan eligibility for active watchers
- safe path handling for source paths under the configured allowlist
- file stability checks using unchanged size and modification time
- SHA-256 calculation for stable files
- deterministic duplicate-suppression keys
- duplicate-suppression observations without duplicate job creation
- creation of new jobs through `DETECTED`, `STABILIZING`, and `REGISTERED`
- outbox enqueueing for `file.detected`, `file.stable`, and `job.registered`
- structured watcher logs and watcher metrics where currently supported

WP-06 verification does not cover validation, quarantine, processing, delivery, retry scheduling, Streamlit UI pages, new API routes, or Docker Compose E2E release evidence.

## Required test files to add or update

| Test file | Required coverage |
|---|---|
| `tests/watcher/test_routing.py` | tag normalization, invalid tag handling, one-to-many routing, many-to-one routing, many-to-many routing, unmatched source `NO_MATCHING_DESTINATION`, unmatched destination `NO_MATCHING_SOURCE` |
| `tests/watcher/test_stability.py` | unstable file before configured window, stable file after unchanged size/mtime, changing file remains unstable, SHA-256 deterministic lower-case hex |
| `tests/watcher/test_deduplication.py` | deterministic key fields, new key not suppressed, existing key suppresses job creation, duplicate observation fields match `SL-FDI-017` |
| `tests/watcher/test_service.py` | `poll_once` happy path, no-file idle observation/no job creation, source outside allowlist rejection without unsafe path leakage, duplicate arrival suppresses events/jobs, inactive or paused watcher does not scan |
| `tests/events/test_outbox.py` or `tests/watcher/test_service.py` | schema-valid `file.detected`, `file.stable`, and `job.registered` outbox rows with watcher/job/file IDs and correlation ID |
| `tests/repositories/test_jobs.py` or `tests/watcher/test_service.py` | state history sequence for `DETECTED`, `STABILIZING`, and `REGISTERED` |

## Minimum WP-06 command suite

Run from the repository root in the project virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/watcher
pytest tests/events
pytest tests/repositories
pytest tests/config tests/api tests/observability
pytest tests/schemas
pytest tests/db
pytest tests/contract
```

## Recommended full regression suite

Run this when WP-06 changes shared repositories, event models, app settings, or Sphinx-visible docs:

```powershell
pytest tests
```

If `pytest tests` is too broad for a first pass, run the minimum WP-06 suite above first, fix failures, then run the full regression suite before final handoff.

## Expected evidence artifacts

| Evidence | Expected update |
|---|---|
| `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md` | Updated only through `python -S tools/contract_lint.py --write-inventory` if requirement references changed. |
| `docs/verification/evidence/schema_fixture_validation.md` | Updated by `python tools/validate_schema_examples.py --write-evidence`. |
| `docs/verification/evidence/sphinx_build.txt` | Updated by `python tools/verify_sphinx_build.py ...`. |
| `docs/worklogs/WORKLOG-<date>-wp06-watcher-implementation.md` | Required worklog for the implementation patch. |
| `docs/verification/evidence_index.md` | Update only if WP-06 retains new evidence files beyond existing schema/Sphinx evidence. |

Do not retain generated Sphinx HTML in a handoff patch. Remove `docs/_build/` before packaging.

## Pass/fail gate

WP-06 is complete only when all of the following are true:

1. `poll_once` can register a new unique stable file into a durable job and state history.
2. The event outbox contains schema-valid `file.detected`, `file.stable`, and `job.registered` events in the expected order for the same job.
3. Duplicate arrivals create duplicate-suppression observations and do not create another job or lifecycle event.
4. Invalid or outside-allowlist source paths are rejected or skipped without leaking unsafe host paths in logs, API-visible fields, events, or errors.
5. Active watchers with no eligible files create no jobs and do not emit failure events.
6. All minimum WP-06 commands pass.
7. A worklog records files changed, requirements affected, decisions applied, tests run, evidence, assumptions, gaps, rollback notes, and next step.

## Cleanup before handoff

Remove generated or local-only artifacts before creating a patch or final handoff snapshot:

- `docs/_build/`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`
- `.venv/`
- `.pytest_vendor/`
- `pytest_vendor/`
- `wheelhouse/`
- `.tmp/`
- `tmp/`
- `pytest-cache-files-*`
