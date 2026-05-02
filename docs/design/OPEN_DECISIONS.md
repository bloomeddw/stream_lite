# Open Design Decisions

This file tracks decisions that should be answered before implementation. As of this patch, the prior six open decisions have been accepted as v0.1 decisions and moved into numbered decision records.

## Current Status

No blocking design decisions remain for requirements-first implementation of the v0.1 Redis Streams + Spark local demo baseline.

Implementation shall not infer behavior outside the accepted decisions below. If a future patch activates Redpanda, Flink, saved dashboard presentation settings, destructive source handling, or validation reprocess workflows, it shall add a new numbered decision record and update requirements before code changes.

## Accepted Decisions

| Previous item | Accepted decision | Decision record | Requirement impact |
|---|---|---|---|
| DEC-TODO-001 Broker Profile for MVP Demo | Use Redis Streams as the only active v0.1 broker; defer Redpanda. | `DEC-003-mvp-broker-profile.md` | REQ-001, REQ-005 |
| DEC-TODO-002 Processing Engine for MVP Demo | Use Spark as the only active v0.1 processing engine; defer Flink. | `DEC-004-mvp-processing-engine.md` | REQ-001, REQ-007 |
| DEC-TODO-003 Quarantine File Handling | Copy invalid files to quarantine and preserve source files unchanged. | `DEC-005-quarantine-file-handling.md` | REQ-004, REQ-013, REQ-015 |
| DEC-TODO-004 Manual Retry Eligibility | Allow manual retry for eligible failed processing/delivery jobs; block validation-policy quarantine retries. | `DEC-006-manual-retry-eligibility.md` | REQ-009, REQ-010, REQ-011 |
| DEC-TODO-005 Dashboard Configuration Storage | Use versioned YAML defaults exposed through a read-only API endpoint; defer persisted presentation mutations. | `DEC-007-dashboard-configuration-storage.md` | REQ-010, REQ-011, REQ-016 |
| DEC-TODO-006 Sphinx Documentation Scope | Build static Sphinx docs first; activate autodoc after code modules exist. | `DEC-008-sphinx-documentation-scope.md` | REQ-014 |

## Deferred Future Decisions

| Topic | Trigger to reopen | Required action before implementation |
|---|---|---|
| Redpanda broker activation | The demo must show Kafka-compatible broker semantics. | Add a new decision, update REQ-001 and REQ-005, add Redpanda env/docs/tests/evidence. |
| Flink processing activation | The demo must show continuous event-time stream processing. | Add a new decision, update REQ-001 and REQ-007, add Flink env/docs/tests/evidence. |
| Saved dashboard presentation settings | Operators need persisted per-user or per-demo presentation choices. | Add a settings storage decision, API mutation requirements, database schema, and verification cases. |
| Validation reprocess/edit workflow | Operators need to fix invalid inputs and reprocess quarantined jobs. | Add reprocess requirements, quarantine release policy, API endpoints, Streamlit controls, and audit requirements. |
| Authentication and roles | Demo moves beyond trusted local operator mode. | Add authN/authZ requirements, route authorization matrix, secrets handling, and tests. |
