# WORKLOG-20260429-l2-requirement-decomposition-batch-2

## Summary

Expanded active requirements from L1-plus-L3 coverage into L1/L2/L3-aligned requirements. The review found that several files had L3 implementation surface rows but did not first define enough L2 contract requirements. This patch adds L2 decomposition across runtime, watcher, file detection, validation, job state, processing, delivery, retry, Streamlit, observability, security, verification, service boundaries, schema governance, and lifecycle orchestration.

## Files Changed

- `docs/reqs/REQ-001-runtime-and-deployment.md`
- `docs/reqs/REQ-002-folder-watch-management.md`
- `docs/reqs/REQ-003-file-detection-and-ingestion.md`
- `docs/reqs/REQ-004-file-validation-and-quarantine.md`
- `docs/reqs/REQ-006-job-metadata-and-state.md`
- `docs/reqs/REQ-007-processing-engine-spark-flink.md`
- `docs/reqs/REQ-008-output-delivery.md`
- `docs/reqs/REQ-009-retry-and-recovery.md`
- `docs/reqs/REQ-011-streamlit-command-center.md`
- `docs/reqs/REQ-012-operational-logging-and-observability.md`
- `docs/reqs/REQ-013-security-and-path-safety.md`
- `docs/reqs/REQ-014-verification-and-acceptance.md`
- `docs/reqs/REQ-015-system-boundaries-and-service-ownership.md`
- `docs/reqs/REQ-016-data-contracts-and-schema-governance.md`
- `docs/reqs/REQ-017-end-to-end-lifecycle-and-handoff-orchestration.md`
- `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`
- `docs/verification/verification_matrix.md`
- `docs/worklogs/BATCH_PROGRESS-20260426-contract-hardening.md`
- `docs/worklogs/WORKLOG-20260429-l2-requirement-decomposition-batch-2.md`

## Requirements Affected

Added L2 decomposition rows:

- `SL-RUN-019` through `SL-RUN-023`
- `SL-FWM-035` through `SL-FWM-039`
- `SL-FDI-025` through `SL-FDI-029`
- `SL-VAL-020` through `SL-VAL-024`
- `SL-JOB-025` through `SL-JOB-030`
- `SL-PRO-024` through `SL-PRO-029`
- `SL-OUT-024` through `SL-OUT-029`
- `SL-RET-016` through `SL-RET-020`
- `SL-UI-042` through `SL-UI-046`
- `SL-OBS-023` through `SL-OBS-027`
- `SL-SEC-013` through `SL-SEC-017`
- `SL-VER-027` through `SL-VER-031`
- `SL-BND-018` through `SL-BND-022`
- `SL-DCT-020` through `SL-DCT-024`
- `SL-LIFE-021` through `SL-LIFE-025`

Existing `REQ-005` and `REQ-010` already contained L2 decomposition and were not expanded in this batch.

## Decisions Applied

- Maintained the active three-level model: L1 capability intent, L2 contract requirements, L3 implementation-surface traceability.
- Preserved the instruction not to create an implementation plan yet.
- Preserved the instruction not to create runtime code before requirements and implementation planning are delineated.
- Preserved `schemas/examples` as the fixture location preference for future fixture work.
- Preserved seconds as the duration metric convention.

## Tests and Verification

Executed:

```bash
python -S tools/contract_lint.py --write-inventory
```

Result:

```text
contract_lint passed
```

Inventory after patch reports zero unresolved requirement references and zero duplicate active requirement rows.

## Assumptions

- L2 rows should be added to the best-fit existing `REQ-###.md` file rather than creating a separate decomposition requirement file.
- L2 rows should remain contract-level and not prescribe source code files unless the row is specifically L3.
- Parent requirement references in L2 rows can point to L1 rows, adjacent L2 rows, and already-defined L3 rows when a contract ties together those concerns.

## Gaps and Next Steps

- Some new L2 rows may still deserve splitting after review, especially lifecycle/recovery rows that span multiple services.
- L3 persistence/repository decomposition is still needed for database tables before migration implementation.
- Endpoint/schema parity, event/schema parity, env-var parity, and metrics parity linting are still pending.
- Invalid examples under `schemas/examples` should be expanded for high-risk API and event schemas.

## Rollback Notes

Rollback by reverting the listed requirement files, verification matrix additions, regenerated inventory, and this worklog/progress update. No runtime code or schema files were changed in this batch.
