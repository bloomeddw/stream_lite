# WORKLOG-20260425: Requirements Clarity and Open Decisions

## Summary

Reviewed the Stream Lite requirements baseline and tightened ambiguous or implementation-risky language so Codex has less room to infer hidden behavior. Added a requirements quality control document and an open decisions register.

## Files changed

- `stream_lite/docs/reqs/REQ-000-requirements-quality-and-ambiguity-control.md`
- `stream_lite/docs/reqs/INDEX.md`
- `stream_lite/docs/reqs/REQ-001-runtime-and-deployment.md`
- `stream_lite/docs/reqs/REQ-002-folder-watch-management.md`
- `stream_lite/docs/reqs/REQ-004-file-validation-and-quarantine.md`
- `stream_lite/docs/reqs/REQ-005-event-streaming.md`
- `stream_lite/docs/reqs/REQ-006-job-metadata-and-state.md`
- `stream_lite/docs/reqs/REQ-007-processing-engine-spark-flink.md`
- `stream_lite/docs/reqs/REQ-008-output-delivery.md`
- `stream_lite/docs/reqs/REQ-009-retry-and-recovery.md`
- `stream_lite/docs/reqs/REQ-010-fastapi-control-plane.md`
- `stream_lite/docs/reqs/REQ-011-streamlit-command-center.md`
- `stream_lite/docs/reqs/REQ-012-operational-logging-and-observability.md`
- `stream_lite/docs/reqs/REQ-013-security-and-path-safety.md`
- `stream_lite/docs/reqs/REQ-014-verification-and-acceptance.md`
- `stream_lite/docs/reqs/CURRENT_REQUIREMENTS_RECAP.md`
- `stream_lite/docs/design/OPEN_DECISIONS.md`
- `stream_lite/docs/design/INDEX.md`
- `stream_lite/docs/master_overview.md`

## Requirements affected

Added `SL-REQ-*` quality and ambiguity-control requirements and tightened runtime, watcher routing, validation/quarantine, events, job state, processing, delivery, retry, API, Streamlit, observability, security, and verification requirements.

## Decisions applied

- Preserved Redis Streams as default broker profile for local demo.
- Preserved Spark as default processing engine for v0.1.
- Treated `tag_match_all_destinations` as the only enabled MVP routing policy.
- Standardized default retry policy to 3 attempts, 1 second initial delay, x2 multiplier, 30 second max delay, jitter enabled.
- Made copy-to-quarantine the local demo quarantine behavior while preserving source files.

## Tests and verification

- Inspected Markdown requirements for ambiguous terms using grep.
- Verified changed files remain under the same top-level `stream_lite/` structure.
- Verified the patch can be packaged as a zip without code changes.

## Assumptions

- MVP remains a local Docker Compose demo rather than Kubernetes/cloud deployment.
- Default broker remains Redis Streams unless you decide otherwise.
- Default processing engine remains Spark unless you decide otherwise.

## Gaps

- API route documentation files under `docs/api/` still need to be created.
- Event JSON schema files under `schemas/` or `docs/schemas/` still need to be created.
- Operations docs for environment variables, Prometheus metrics, retry policy, quarantine policy, Docker Compose, and runbook still need to be created.
- Sphinx configuration and verification matrix files still need to be created.

## Rollback notes

To roll back, restore the previous requirements files from the prior zip or remove the files added by this patch and revert the edited Markdown sections listed above.

## Next step

Confirm the open decisions in `stream_lite/docs/design/OPEN_DECISIONS.md`, then create the API, schema, environment, metrics, retry/quarantine, Sphinx, and verification matrix docs before implementation.
