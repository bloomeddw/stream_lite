# REQ-014: Verification and Acceptance Requirements

## Capability Intent

The system shall define done as verified behavior, not merely implemented code. Each capability shall have named verification cases, expected evidence artifacts, and measurable acceptance conditions.

## Verification Evidence Convention

Evidence root:

```text
stream_lite/docs/verification/<verification_id>/
```

Minimum evidence artifacts:

- `case_manifest.json`
- `inputs/`
- `actual/`
- `expected/`
- `comparison.json`
- `summary.md`

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-VER-001 | Each requirement document shall include unique requirement IDs. | Must | V-SL-VER-001 |
| SL-VER-002 | Each must-level requirement shall map to at least one verification case. | Must | V-SL-VER-002 |
| SL-VER-003 | Verification shall include unit, integration, schema, API, event replay, failure injection, Docker Compose smoke, Streamlit manual, Sphinx build, metrics, and end-to-end demo tests. | Must | V-SL-VER-003 |
| SL-VER-004 | Verification shall include a fixture set for valid files. | Must | V-SL-VER-004 |
| SL-VER-005 | Verification shall include a fixture set for invalid files. | Must | V-SL-VER-005 |
| SL-VER-006 | Verification shall include duplicate detection tests. | Must | V-SL-VER-006 |
| SL-VER-007 | Verification shall include service restart recovery tests. | Must | V-SL-VER-007 |
| SL-VER-008 | Verification shall include event replay/idempotency tests. | Must | V-SL-VER-008 |
| SL-VER-009 | Verification shall include dashboard-driven happy path demo test. | Should | V-SL-VER-009 |
| SL-VER-010 | Verification shall include path safety tests. | Must | V-SL-VER-010 |
| SL-VER-011 | Verification summaries shall report pass/fail status and measured values for metric requirements. | Must | V-SL-VER-011 |
| SL-VER-012 | The product demo shall not be accepted unless the end-to-end happy path and invalid-file quarantine path both pass. | Must | V-SL-VER-012 |
| SL-VER-013 | Verification shall include an idle watcher test that proves no jobs are created when configured source folders are empty. | Must | V-SL-VER-013 |
| SL-VER-014 | Verification shall include source and destination health indicator tests for green, yellow, and red states. | Must | V-SL-VER-014 |
| SL-VER-015 | Verification shall include a dashboard folder browse and path validation test. | Must | V-SL-VER-015 |
| SL-VER-016 | Verification shall include tag normalization tests for semicolon-delimited source and destination route tags. | Must | V-SL-VER-016 |
| SL-VER-017 | Verification shall include route preview tests for one-to-one, one-to-many, many-to-one, and many-to-many tag matching. | Must | V-SL-VER-017 |
| SL-VER-018 | Verification shall include partial multi-destination delivery failure tests proving per-destination outcomes. | Must | V-SL-VER-018 |
| SL-VER-019 | Verification shall include dashboard presentation configuration tests proving color tokens and layout profiles are loaded centrally. | Must | V-SL-VER-019 |
| SL-VER-023 | Verification shall include lifecycle handoff tests that stop and restart one service at each stage boundary and prove the job resumes without duplicate side effects. | Must | V-SL-VER-023 |
| SL-VER-024 | Verification shall include command status tests proving accepted `202` commands reach terminal command status and expose failure details when a command fails after acceptance. | Must | V-SL-VER-024 |
| SL-VER-025 | Verification shall include transactional outbox tests proving committed state changes eventually publish events after broker outage recovery. | Must | V-SL-VER-025 |
| SL-VER-026 | Verification shall include backpressure tests proving eligible jobs remain durable when worker concurrency limits are reached. | Must | V-SL-VER-026 |

## Required Verification Matrix

| Verification ID | Purpose | Evidence |
|---|---|---|
| V-SL-DEMO-001 | Single source to single destination happy path | API logs, job records, events, output files, dashboard screenshots optional |
| V-SL-DEMO-002 | Multi-source watcher happy path | watcher config, jobs, output manifests |
| V-SL-DEMO-003 | Invalid file quarantine | validation results, quarantine locator, reason codes |
| V-SL-DEMO-004 | Duplicate file suppression | duplicate fixture inputs, job counts, comparison report |
| V-SL-DEMO-005 | Processing retry after transient failure | retry records, attempts, final state |
| V-SL-DEMO-006 | Delivery retry after transient failure | delivery attempts, output manifest, final state |
| V-SL-DEMO-007 | Restart recovery | pre/post restart records, pending job completion |
| V-SL-DEMO-008 | Event replay idempotency | duplicate events, single job/output result |
| V-SL-DEMO-009 | Dashboard command-center flow | operator action log and API records |
| V-SL-DEMO-010 | Path safety | rejected payloads and API error codes |
| V-SL-DEMO-011 | Idle watcher with empty source folders | watcher status records, zero job count, dashboard idle evidence |
| V-SL-DEMO-012 | Source/destination health dots | fixture folders, API health responses, dashboard evidence for green/yellow/red |
| V-SL-DEMO-013 | Dashboard browse folder flow | API browse responses, selected folder config, validation responses |
| V-SL-DEMO-014 | Tag-based route normalization and preview | Tag fixtures, API preview responses, dashboard preview evidence |
| V-SL-DEMO-015 | Many-to-many delivery through shared route tags | Source/destination configs, delivery attempts, output manifests, matched tag records |
| V-SL-DEMO-016 | Partial multi-destination failure | Delivery attempt records, red destination health, partial terminal state evidence |
| V-SL-DEMO-017 | Dashboard centralized presentation configuration | Theme/layout config, API response, dashboard screenshot or state evidence |
| V-SL-DEMO-018 | Lifecycle handoff restart recovery | Restart fixtures at detection, validation, processing, delivery, retry, and outbox boundaries |
| V-SL-DEMO-019 | Command acceptance and completion | Command records, command status API responses, dashboard polling evidence |
| V-SL-DEMO-020 | Transactional outbox broker outage recovery | Outbox records before and after broker outage, published event evidence |
| V-SL-DEMO-021 | Backpressure and concurrency limits | Worker limit configuration, queued job counts, queue lag metrics |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-VER-NFR-001 | Must requirement verification coverage | 100% |
| SL-VER-NFR-002 | Critical end-to-end demo pass rate before acceptance | 100% |
| SL-VER-NFR-003 | Fixture comparison outputs machine-readable | 100% |
| SL-VER-NFR-004 | Metric requirements reported with actual measured value | 100% where measurable in local demo |
| SL-VER-NFR-005 | Failed verification cases include failure reason | 100% |
| SL-VER-NFR-006 | Tag routing verification fixture coverage | 100% of one-to-one, one-to-many, many-to-one, and many-to-many scenarios |

## L2 Contract Decomposition Requirements

These rows decompose verification into coverage, evidence, acceptance scenario, manual validation, and readiness-gate contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-VER-027 | L2 | SL-VER-001, SL-VER-002, SL-DECOMP-009 | Requirement coverage contract | Each active `Must` requirement shall map to at least one verification ID, method, evidence artifact, and status before implementation planning starts. | Must | V-SL-VER-027 |
| SL-VER-028 | L2 | SL-VER-003, SL-VER-004 | Evidence artifact contract | Evidence artifacts shall be stored under documented evidence paths, named by verification ID or scenario, include execution timestamp when generated, and be reproducible from documented commands or checklists. | Must | V-SL-VER-028 |
| SL-VER-029 | L2 | SL-VER-005, SL-VER-006, SL-VER-026 | Acceptance test scenario contract | Acceptance scenarios shall identify preconditions, inputs, operator actions, expected API responses, expected events, expected database states, expected metrics/logs, and cleanup/reset steps. | Must | V-SL-VER-029 |
| SL-VER-030 | L2 | SL-VER-007, SL-VER-008 | Manual validation contract | Streamlit and demo-usefulness validation shall use manual checklists with requirement IDs, visible UI evidence, expected operator messages, and pass/fail notes. | Must | V-SL-VER-030 |
| SL-VER-031 | L2 | SL-VER-009, SL-VER-010 | Release readiness gate contract | A milestone shall not be ready unless contract lint, schema validation, verification coverage, Sphinx build where applicable, and known gaps are recorded in the worklog. | Must | V-SL-VER-031 |

## Acceptance Criteria

The requirements baseline is accepted when every must-level requirement maps to a verification case and the defined end-to-end demo paths produce evidence artifacts proving idle behavior, source/destination folder validation, route tag normalization, many-to-many tag matching, source detection, validation, event publication, metadata persistence, processing, per-destination delivery, retry behavior, partial delivery failure visibility, centralized dashboard presentation configuration, health-dot dashboard visibility, and dashboard folder browsing, lifecycle handoff restart recovery, command-status tracking, outbox recovery, and backpressure behavior.

## Verification Matrix Minimum Columns

The verification matrix shall include the following columns: `verification_id`, `requirement_ids`, `method`, `preconditions`, `steps`, `expected_result`, `measured_value`, `evidence_artifact`, `status`, `run_timestamp`, and `notes`.

## Evidence Artifact Paths

| Evidence type | Required path pattern |
|---|---|
| API test output | `stream_lite/evidence/api/<run_id>/` |
| Event replay output | `stream_lite/evidence/events/<run_id>/` |
| Failure injection output | `stream_lite/evidence/failures/<run_id>/` |
| Docker Compose smoke output | `stream_lite/evidence/docker/<run_id>/` |
| Streamlit manual checklist | `stream_lite/evidence/streamlit/<run_id>/` |
| Sphinx build output | `stream_lite/evidence/sphinx/<run_id>/` |
| End-to-end demo output | `stream_lite/evidence/e2e/<run_id>/` |

## Sphinx Documentation Verification Scope

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-VER-020 | v0.1 Sphinx verification shall build static documentation pages for requirements, architecture/design, operations, API contracts, schemas, verification, and worklogs before code autodoc is required. | Must | V-SL-VER-020 |
| SL-VER-021 | Python autodoc pages shall be required only after route handlers, validators, event producers/consumers, processors, and retry handlers exist in source code. | Must | V-SL-VER-021 |
| SL-VER-022 | A missing future autodoc target shall not fail the v0.1 static documentation build; it shall be listed as deferred in the Sphinx evidence summary. | Must | V-SL-VER-022 |

## Applied Decision Records

| Decision | Requirement impact |
|---|---|
| DEC-008 Sphinx documentation scope | v0.1 requires static Sphinx documentation first; autodoc is activated after code modules exist. |

## 2026-04-25 Decomposed Verification Artifacts

The active verification decomposition lives in:

- `docs/verification/verification_matrix.md`
- `docs/verification/acceptance_test_plan.md`
- `docs/verification/evidence_index.md`

Implementation planning shall use these files as the source of truth for test task creation and evidence collection. New code tasks shall add or update verification rows before implementation when they introduce new routes, events, tables, env vars, metrics, Streamlit controls, or failure paths.
