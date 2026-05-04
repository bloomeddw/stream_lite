# Post-WP-05 Reference Maps

This folder contains documentation-only implementation maps for work packages after WP-05. The files are not prompts and do not authorize Codex to start later work early. They reduce reasoning burden by turning the existing requirements, schemas, repositories, and verification expectations into fixed maps that later Codex prompts can reference.

Use these maps after WP-05 is complete and verified:

| Work package | Reference file | Purpose |
|---|---|---|
| WP-06 | `WP06_WATCHER_REFERENCE.md` | Watcher configuration, route matching, detection, stability, duplicate suppression, and job registration handoff. |
| WP-07 | `WP07_VALIDATION_QUARANTINE_REFERENCE.md` | File validation, validation attempts, quarantine artifact creation, quarantine copy behavior, and validation events. |
| WP-08 | `WP08_PROCESSING_REFERENCE.md` | Processing stage claim, Spark-profile processing adapter, processing attempts, processing artifacts, and processing events. |
| WP-09 | `WP09_DELIVERY_REFERENCE.md` | Delivery fanout, destination outcomes, output manifest writing, and delivery events. |
| WP-09 low-reasoning split | `WP09_LOW_REASONING_DELIVERY_MICROPLAN.md` | Two-step WP09-A/WP09-B map separating routing/filesystem/manifest work from worker/state/event integration. |
| WP-10 | `WP10_RETRY_REFERENCE.md` | Retry classification, backoff, retry scheduling, exhausted retry behavior, and manual retry command primitives. |
| WP-11 | `WP11_STREAMLIT_REFERENCE.md` | API-backed Streamlit command center pages, controls, state polling, theme/layout use, and manual evidence. |
| WP-12 | `WP12_OBSERVABILITY_REFERENCE.md` | Metrics, structured logs, redaction, operational summaries, health observations, and API/dashboard integration points. |
| WP-13 | `WP13_SPHINX_REFERENCE.md` | Static/autodoc Sphinx build completion and docs verification evidence. |
| WP-14 | `WP14_E2E_RELEASE_REFERENCE.md` | End-to-end demo flows, release evidence, smoke scripts, and final verification closure. |

## Common guardrails for all future work packages

- Do not restore `REQ-018`.
- Do not start a later work package until the current package worklog and verification evidence show the current package is complete.
- Use the virtual environment in the working directory before running dependency-backed checks:
  ```powershell
  cd C:\Users\asosa\stream_lite
  .\.venv\Scripts\Activate.ps1
  python -m pip install -r requirements-dev.txt
  ```
- Do not vendor dependencies into `.pytest_vendor/`, `pytest_vendor/`, or `wheelhouse/`.
- Do not include generated/cache artifacts in handoff snapshots: `docs/_build/`, `.pytest_cache/`, `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_vendor/`, `pytest_vendor/`, `wheelhouse/`, `.tmp/`, or `pytest-cache-files-*`.
- Keep JSON schemas authoritative. Pydantic models and runtime code may validate against those contracts but must not redefine the contracts silently.
- Every work package needs a worklog in `docs/worklogs/` with summary, files changed, requirements affected, decisions applied, verification commands/results, assumptions, gaps, rollback notes, and next step.
