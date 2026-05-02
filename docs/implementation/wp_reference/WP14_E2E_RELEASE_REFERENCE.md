# WP-14 Reference Map: End-to-End Demo Flow and Release Evidence

## Purpose

Reduce Codex reasoning for WP-14 by fixing the final demo flows, smoke evidence, reset/rollback behavior, and release-readiness gates.

## Scope boundary

WP-14 proves the complete Stream Lite demo. It may add E2E tests, smoke scripts, evidence docs, and small glue needed to run the demo, but it must not invent new product behavior.

## Primary requirement IDs

- `SL-LIFE-001` through `SL-LIFE-020`
- `SL-VER-001` through `SL-VER-030`
- All implemented capability requirements from WP-00 through WP-13

## Read before coding

- `docs/verification/verification_matrix.md`
- `docs/verification/acceptance_test_plan.md`
- `docs/verification/evidence_index.md`
- `docs/operations/runbook.md` if present
- `docs/operations/docker_compose.md` if present
- `docs/operations/maintenance.md` if present
- `docs/implementation/CODEX_TASK_GUIDE.md`
- all worklogs from WP-00 onward

## Target files

| File/folder | Responsibility |
|---|---|
| `tests/e2e/` | Automated E2E flows where feasible. |
| `tests/smoke/` | Docker Compose or local smoke checks where feasible. |
| `tools/run_demo_smoke.py` or equivalent | Optional smoke runner if requirement-backed. |
| `docs/verification/evidence/e2e_demo_run.md` | Final evidence summary. |
| `docs/verification/evidence/docker_compose_smoke.md` | Compose smoke evidence if Compose exists. |
| `docs/operations/runbook.md` | Ensure startup/shutdown/reset commands are current. |

## Fixed demo flows

### Flow A: valid file happy path

1. Configure source/destination route tags.
2. Start watcher.
3. Place valid file in source.
4. Observe file detected/stable/job registered events.
5. Validate file.
6. Process file.
7. Deliver output to matching destinations.
8. Confirm final job state `COMPLETED`.
9. Confirm output manifest and processing summary artifacts.
10. Confirm dashboard/API visibility.

### Flow B: validation failure quarantine

1. Place invalid file in source.
2. Observe validation failure.
3. Confirm file is quarantined.
4. Confirm quarantine record artifact.
5. Confirm final quarantine/invalid job state as documented.
6. Confirm no processing/delivery occurs.

### Flow C: retry/exhaustion

1. Induce recoverable processing or delivery failure.
2. Confirm retry schedule is created.
3. Confirm retries obey backoff and max attempts.
4. Confirm exhausted retries produce final failure and dead-letter/job failure behavior.

### Flow D: operator dashboard smoke

1. Open Streamlit command center.
2. Confirm health, watchers, jobs, events, quarantine, outputs, logs, metrics summaries are visible.
3. Confirm safe controls trigger API commands and command status polling.

## Evidence requirements

Each E2E evidence file should include:

- command executed
- timestamp
- environment/profile
- input files used
- observed job IDs/correlation IDs
- event IDs
- API responses or summarized outputs
- artifact paths/locators
- final state
- pass/fail result
- cleanup performed

## Reset and rollback

Document cleanup commands for:

- stopping services
- clearing source/destination/quarantine demo folders
- resetting Redis streams
- resetting PostgreSQL volume/tables
- removing generated artifacts

## Test checklist

- Valid file E2E passes.
- Invalid file quarantine E2E passes.
- Retry/exhaustion E2E passes or is documented as manual/limited with reason.
- Streamlit manual checklist is complete.
- Verification matrix rows for implemented requirements have evidence links.
- No generated/cache artifacts are committed.

## Out of scope

- New architecture.
- New APIs/events/schemas not already requirement-backed.
- Performance/load testing beyond demo requirements unless already scoped.

## Verification commands

Run the full suite and E2E/smoke commands:

```powershell
pytest tests/contract
pytest tests/config tests/api tests/observability
pytest tests/schemas
pytest tests/db tests/repositories
pytest tests/events
pytest tests/watcher tests/validation tests/processing tests/delivery tests/retry
pytest tests/e2e
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
```

Use Docker Compose smoke commands only if the repo has Compose files and ops docs by WP-14.
