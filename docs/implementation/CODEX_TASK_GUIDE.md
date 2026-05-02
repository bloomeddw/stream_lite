# Codex Task Guide

## Purpose

This guide converts the accepted Stream Lite requirements and contract artifacts into ordered, code-ready work packages for Codex. It is not runtime code and it does not authorize architecture changes outside the documented contracts.

Codex SHALL implement only behavior that is backed by requirement IDs, schema files, API contracts, event contracts, environment-variable docs, metrics docs, and verification rows. When a requirement, interface, schema, route, retry rule, metric, log field, or state transition is unclear, Codex SHALL stop and request requirement clarification instead of inventing behavior.


## Mandatory Agent Safety Gate

Before any implementation work, Codex SHALL read `AGENTS.md`, `RULES.md`. These files override any prompt text that would cause cleanup deletion, broad cleanup, recursive deletion, repository reset, or removal of source/docs/schema/test/evidence/worklog files. Generated artifacts must be excluded from patches by explicit zip include/exclude rules, not by deleting the working tree. If a prompt says to remove generated artifacts, Codex SHALL interpret that as package exclusion unless the user explicitly names exact files to delete. Codex SHALL NOT run targeted-looking cleanup loops that combine repo-root variables such as `$root`, `$PWD`, or `Resolve-Path .` with `Remove-Item`, `rm`, `del`, `find -delete`, or recursive path discovery.

## Required Codex Response Format for Each Coding Task

Each Codex implementation response SHALL include:

| Section | Required content |
|---|---|
| Scope | One work package from this guide and explicit out-of-scope items. |
| Requirements implemented | Requirement IDs and verification IDs touched. |
| Files changed | Target modules, tests, docs, schemas, and generated evidence. |
| Contract usage | API schemas, event schemas, artifact schemas, env vars, metrics, and routes used. |
| Tests run | Exact commands and outcomes. |
| Evidence artifacts | Paths to pytest output, schema validation output, Sphinx output, metrics/log evidence, or manual evidence notes. |
| Rollback notes | Files to revert and state/data cleanup notes. |
| Gaps | Any requirement ambiguity or unimplemented behavior. |

## Global Coding Rules

1. Preserve the repository top-level structure under `stream_lite/`.
2. Do not add env vars unless they are added to requirements, `.env.example`, and `docs/operations/environment_variables.md` in the same patch.
3. Do not add API routes unless they are documented in `docs/api/endpoints.md`, mapped in `docs/schemas/api_schemas.md`, and covered by `REQ-010` plus verification rows.
4. Do not emit events unless they have a JSON schema in `schemas/events/`, examples under `schemas/examples/events/`, and an event row in `docs/schemas/events.md`.
5. Do not create persistence tables or repository methods unless they map to `docs/data/migration_plan.md`, `docs/data/logical_model.md`, and the L3 persistence rows in `REQ-006`.
6. Use application-owned UUID generation before insert as decided in `docs/design/DEC-009-uuid-generation-ownership.md`.
7. Use duration metrics in seconds. Do not introduce `_duration_ms` metrics.
8. All logs SHALL follow the structured-log field contract in `REQ-012` and must not log secrets or unsafe host paths.
9. Every patch SHALL run `python -S tools/contract_lint.py --write-inventory` before packaging.
10. Every code patch SHALL include or update tests and verification evidence.

## Target Package Layout

The naming below is the expected starting layout for implementation. Codex may add small helper modules inside these packages only when the helper purpose is directly traceable to the work package requirements.

```text
stream_lite/
  app/
    __init__.py
    api/
      __init__.py
      main.py
      dependencies.py
      errors.py
      routes/
        __init__.py
        health.py
        metrics.py
        watchers.py
        jobs.py
        events.py
        files.py
        config.py
        operations.py
      schemas/
        __init__.py
        api_models.py
    config/
      __init__.py
      settings.py
      path_policy.py
    db/
      __init__.py
      base.py
      session.py
      migrations/
    repositories/
      __init__.py
      watchers.py
      files.py
      jobs.py
      validation.py
      processing.py
      delivery.py
      retry.py
      commands.py
      stage_claims.py
      events.py
      logs.py
      health.py
    events/
      __init__.py
      models.py
      outbox.py
      dispatcher.py
      redis_streams.py
    watcher/
      __init__.py
      service.py
      stability.py
      routing.py
      deduplication.py
    validation/
      __init__.py
      validator.py
      quarantine.py
    processing/
      __init__.py
      engine.py
      spark_adapter.py
    delivery/
      __init__.py
      service.py
    retry/
      __init__.py
      scheduler.py
      classifier.py
      backoff.py
    observability/
      __init__.py
      logging.py
      metrics.py
      summaries.py
  streamlit_app/
    __init__.py
    main.py
    pages/
      health.py
      watchers.py
      jobs.py
      events.py
      quarantine.py
      outputs.py
      logs.py
      config.py
  tests/
```

## Work Package Order

Codex SHALL implement packages in the order below unless a later design decision changes the dependency order.

### WP-00 Contract Validation and Developer Verification Harness

| Field | Content |
|---|---|
| Goal | Make contract validation executable before runtime code is generated. |
| Requirement IDs | SL-DCT-022, SL-DCT-024, SL-DCT-025, SL-DCT-026, SL-DCT-027, SL-DCT-028, SL-REQ-004, SL-DECOMP-009 |
| Target files/modules | `requirements-dev.txt`, `tools/validate_schema_examples.py`, `tests/contract/test_schema_examples.py`, `tools/contract_lint.py`, `docs/sphinx_build.md` |
| Schemas used | All schemas under `schemas/api/`, `schemas/events/`, and `schemas/artifacts/`; all examples under `schemas/examples/`. |
| Repository/API/event surfaces | None; this is pre-runtime verification. |
| Expected tests | JSON Schema fixture validation; contract lint; optional Sphinx build when Sphinx is installed. |
| Evidence artifacts | `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md`, `docs/verification/evidence/schema_fixture_validation.md`, `docs/verification/evidence/sphinx_build.txt`. |
| Rollback notes | Remove validation harness files and evidence only; no database or runtime state exists. |

### WP-01 Project Skeleton, Settings, and Shared Types

| Field | Content |
|---|---|
| Goal | Create the minimal Python package structure, configuration loader, UUID helper, path policy primitives, shared result types, and test harness. |
| Requirement IDs | SL-RUN-001 through SL-RUN-010, SL-SEC-001 through SL-SEC-017, SL-DCT-001 through SL-DCT-008 |
| Target files/modules | `app/config/settings.py`, `app/config/path_policy.py`, `app/api/errors.py`, `app/observability/logging.py`, package `__init__.py` files. |
| Schemas used | `schemas/api/standard_error.schema.json`, `schemas/api/path_validation_request.schema.json`, `schemas/api/path_validation_response.schema.json`. |
| Repository/API/event surfaces | No persistence; shared types only. |
| Expected tests | Settings validation, missing/invalid env behavior, local-demo trusted-mode defaults, path allowlist rejection, safe-path display. |
| Evidence artifacts | pytest output and updated requirement inventory. |
| Rollback notes | Revert package skeleton and settings files; no durable state. |

### WP-02 Pydantic Models and Schema Binding

| Field | Content |
|---|---|
| Goal | Implement Pydantic models that mirror JSON schemas without weakening contracts. |
| Requirement IDs | SL-DCT-001 through SL-DCT-028, SL-API-031 through SL-API-040, SL-EVT-001 through SL-EVT-023 |
| Target files/modules | `app/api/schemas/api_models.py`, `app/events/models.py`, `app/validation/models.py`, `app/processing/models.py`, `app/delivery/models.py`. |
| Schemas used | All API, event, and artifact JSON schemas. |
| Repository/API/event surfaces | Model classes for API request/response bodies, event envelopes, and artifact records. |
| Expected tests | Round-trip validation from valid examples; expected failure from invalid examples; enum/timestamp/path invalid example failures. |
| Evidence artifacts | schema fixture validation output and pytest output. |
| Rollback notes | Revert model modules and generated docs; no database state. |

### WP-03 Database Migrations and Repository Interfaces

| Field | Content |
|---|---|
| Goal | Add Alembic scaffolding and repository interfaces for durable state, without implementing business workers yet. |
| Requirement IDs | SL-JOB-001 through SL-JOB-051, SL-LIFE-009, SL-LIFE-015, SL-EVT-011, SL-EVT-015, SL-VAL-016, SL-RET-006, SL-RET-012 |
| Target files/modules | `app/db/base.py`, `app/db/session.py`, `app/db/migrations/`, `app/repositories/*.py`. |
| Schemas used | Artifact schemas for quarantine, processing summary, and output manifest; event outbox event schemas. |
| Repository/API/event surfaces | `WatcherRepository`, `FileRepository`, `JobRepository`, `ValidationRepository`, `ProcessingRepository`, `DeliveryRepository`, `RetryRepository`, `CommandRepository`, `StageClaimRepository`, `EventOutboxRepository`, `EventOffsetRepository`, `OperationalLogRepository`, `HealthRepository`. |
| Expected tests | Alembic upgrade/downgrade smoke; repository insert/read/update tests; UUID ownership tests; idempotency uniqueness tests. |
| Evidence artifacts | migration logs, pytest output, contract lint output. |
| Rollback notes | Downgrade migrations or reset Docker Compose database volume; revert repository files. |

### WP-04 Event Outbox, Redis Streams, and Dispatcher

| Field | Content |
|---|---|
| Goal | Implement durable event enqueueing, Redis stream publication, offsets, dead-letter behavior, and event listing support. |
| Requirement IDs | SL-EVT-001 through SL-EVT-023, SL-JOB-048, SL-JOB-049, SL-LIFE-010, SL-LIFE-011, SL-OBS-006 |
| Target files/modules | `app/events/outbox.py`, `app/events/dispatcher.py`, `app/events/redis_streams.py`, `app/repositories/events.py`. |
| Schemas used | All event schemas and event examples. |
| Repository/API/event surfaces | `EventOutboxRepository.enqueue_event`, `mark_published`, `mark_dead_lettered`, `EventOffsetRepository.upsert_offset`, `EventDispatcher.publish_due_events`. |
| Expected tests | Outbox transaction tests, publish retry tests, dead-letter tests, schema validation of emitted events, offset persistence tests. |
| Evidence artifacts | pytest output, event fixture validation, event-flow evidence. |
| Rollback notes | Stop dispatcher, clear pending outbox rows if demo-only, reset Redis stream data. |

### WP-05 FastAPI App Shell and Control Plane Routes

| Field | Content |
|---|---|
| Goal | Implement documented local-demo API routes using existing schemas, repositories, metrics, and structured errors. |
| Requirement IDs | SL-API-001 through SL-API-050, SL-OBS-001 through SL-OBS-012, SL-SEC-010, SL-SEC-011 |
| Target files/modules | `app/api/main.py`, `app/api/dependencies.py`, `app/api/routes/health.py`, `metrics.py`, `watchers.py`, `jobs.py`, `events.py`, `files.py`, `config.py`, `operations.py`, `app/api/errors.py`. |
| Schemas used | All API schemas in `schemas/api/`. |
| Repository/API/event surfaces | Route handlers named in `docs/implementation/naming_review.md`; repositories from WP-03; event surfaces from WP-04. |
| Expected tests | API route tests for status codes, schemas, idempotency, pagination, filters, command polling, and error envelope behavior. |
| Evidence artifacts | API pytest output and OpenAPI snapshot if generated. |
| Rollback notes | Revert route modules; no migration rollback unless routes created data during manual testing. |

Detailed low-reasoning implementation map and continuation prompt: `docs/implementation/wp_reference/WP05_FASTAPI_CONTROL_PLANE_MAP.md` and `docs/implementation/WP05_CODEX_PROMPT.md`.

Supporting low-reasoning reference maps for WP-06 through WP-14 live under `docs/implementation/wp_reference/`. These files should be used by later prompts after WP-05 is complete, but they do not start or authorize later work packages by themselves.

### WP-06 Watcher Configuration, Routing, Detection, Stability, and Deduplication

| Field | Content |
|---|---|
| Goal | Implement folder watchers, route-tag matching, file stability checks, file identity, duplicate suppression, and job registration handoff. |
| Requirement IDs | SL-FWM-001 through SL-FWM-031, SL-FDI-001 through SL-FDI-029, SL-JOB-035, SL-JOB-036, SL-LIFE-001 through SL-LIFE-006 |
| Target files/modules | `app/watcher/service.py`, `app/watcher/stability.py`, `app/watcher/routing.py`, `app/watcher/deduplication.py`, `app/repositories/watchers.py`, `app/repositories/files.py`, `app/repositories/jobs.py`. |
| Schemas used | `file_detected`, `file_stable`, `job_registered` event schemas; watcher API schemas. |
| Repository/API/event surfaces | `WatcherService.start/stop/poll_once`, `RouteMatcher.preview_routes`, `FileStabilityDetector.is_stable`, `DuplicateSuppressionService.check_or_record`. |
| Expected tests | Route matching matrix tests, stability timing tests, duplicate suppression tests, job registration tests, event enqueue tests. |
| Evidence artifacts | watcher unit/integration pytest output and event-flow evidence. |
| Rollback notes | Stop watcher process; clear demo folders and watcher/job rows if needed. |

Detailed implementation map: `docs/implementation/wp_reference/WP06_WATCHER_REFERENCE.md`. Post-implementation verification plan: `docs/implementation/WP06_VERIFICATION_PLAN.md`.

### WP-07 Validation and Quarantine

| Field | Content |
|---|---|
| Goal | Validate stable files, persist validation attempts, quarantine invalid files, and emit validation/quarantine events. |
| Requirement IDs | SL-VAL-001 through SL-VAL-024, SL-JOB-038, SL-JOB-039, SL-LIFE-007, SL-SEC-012, SL-OBS-004 |
| Target files/modules | `app/validation/validator.py`, `app/validation/quarantine.py`, `app/repositories/validation.py`, `app/events/outbox.py`, `app/observability/metrics.py`. |
| Schemas used | `file_validated`, `file_quarantined`, `quarantine_record.schema.json`. |
| Repository/API/event surfaces | `FileValidator.validate_file`, `QuarantineService.quarantine_file`, `ValidationRepository.create_attempt`, `create_quarantine_record`. |
| Expected tests | Extension/size/readability validation tests, immediate quarantine tests, safe path tests, schema validation for events/artifacts. |
| Evidence artifacts | validation pytest output, quarantine artifact fixture output. |
| Rollback notes | Remove quarantined demo files and related rows; revert validation modules. |

### WP-08 Processing Worker

| Field | Content |
|---|---|
| Goal | Implement the MVP processing adapter and processing attempt lifecycle. |
| Requirement IDs | SL-PRO-001 through SL-PRO-029, SL-JOB-040, SL-LIFE-008, SL-OBS-005 |
| Target files/modules | `app/processing/engine.py`, `app/processing/spark_adapter.py`, `app/repositories/processing.py`, `app/events/outbox.py`. |
| Schemas used | `processing_started`, `processing_completed`, `processing_failed`, `processing_summary.schema.json`. |
| Repository/API/event surfaces | `ProcessingWorker.claim_and_process`, `ProcessingRepository.create_attempt`, `ProcessingSummaryWriter.write_summary`. |
| Expected tests | Stage claim tests, processing success/failure tests, artifact schema validation, duration metric tests. |
| Evidence artifacts | processing pytest output and sample processing summary. |
| Rollback notes | Remove generated output artifacts and processing rows. |

### WP-09 Delivery Worker

| Field | Content |
|---|---|
| Goal | Copy processed outputs to matched destinations with per-destination results and output manifest generation. |
| Requirement IDs | SL-OUT-001 through SL-OUT-029, SL-JOB-041, SL-JOB-042, SL-LIFE-012, SL-OBS-007 |
| Target files/modules | `app/delivery/service.py`, `app/repositories/delivery.py`, `app/events/outbox.py`. |
| Schemas used | `delivery_started`, `delivery_completed`, `delivery_failed`, `output_manifest.schema.json`. |
| Repository/API/event surfaces | `DeliveryWorker.claim_and_deliver`, `DeliveryRepository.create_attempt`, `OutputManifestWriter.write_manifest`. |
| Expected tests | Multi-destination fanout tests, partial failure tests, manifest validation tests, destination safe-path tests. |
| Evidence artifacts | delivery pytest output and sample manifest. |
| Rollback notes | Remove delivered demo files and output manifest rows. |

### WP-10 Retry Scheduler and Manual Retry

| Field | Content |
|---|---|
| Goal | Implement retry classification, exponential backoff, exhausted retry behavior, dead-letter handoff, and manual retry command handling. |
| Requirement IDs | SL-RET-001 through SL-RET-020, SL-JOB-043, SL-JOB-044, SL-LIFE-014, SL-EVT-017, SL-EVT-022, SL-EVT-023 |
| Target files/modules | `app/retry/classifier.py`, `app/retry/backoff.py`, `app/retry/scheduler.py`, `app/repositories/retry.py`, `app/repositories/commands.py`. |
| Schemas used | `retry_scheduled`, `job_failed`, `lifecycle_command_request`, `retry_command_request`, `command_accepted_response`, `command_status_response`. |
| Repository/API/event surfaces | `RetryClassifier.classify`, `BackoffPolicy.next_delay_seconds`, `RetryScheduler.schedule_due_retries`, `ManualRetryService.accept_command`. |
| Expected tests | Retryable/non-retryable classification, backoff with jitter bounds, max attempt exhaustion, manual retry eligibility and idempotency. |
| Evidence artifacts | retry pytest output and retry event evidence. |
| Rollback notes | Clear retry schedules/control commands and reset affected demo job states. |

### WP-11 Streamlit Command Center

| Field | Content |
|---|---|
| Goal | Implement the operator dashboard as an API-backed command center. |
| Requirement IDs | SL-UI-001 through SL-UI-030, SL-API-031 through SL-API-040, SL-OBS-009, SL-OBS-010 |
| Target files/modules | `streamlit_app/main.py`, `streamlit_app/pages/*.py`, optional `streamlit_app/api_client.py`, `streamlit_app/theme.py`, `streamlit_app/layout.py`. |
| Schemas used | API response schemas for health, watchers, jobs, events, logs, metrics, route preview, command status. |
| Repository/API/event surfaces | FastAPI only; Streamlit SHALL NOT write directly to the database in MVP. |
| Expected tests | Manual Streamlit checklist, API-client unit tests, command polling behavior, theme/layout configuration checks. |
| Evidence artifacts | screenshots or manual evidence notes, API logs, Streamlit action metrics. |
| Rollback notes | Revert Streamlit files; no database migration rollback. |

### WP-12 Observability, Metrics, Logging, and Summary Logs

| Field | Content |
|---|---|
| Goal | Implement shared metrics, structured logs, redaction, operational summaries, and dashboard metric summaries. |
| Requirement IDs | SL-OBS-001 through SL-OBS-027, SL-SEC-015, SL-API-033, SL-UI-012 |
| Target files/modules | `app/observability/logging.py`, `app/observability/metrics.py`, `app/observability/summaries.py`, route integration points. |
| Schemas used | `metrics_summary_response`, `operational_log_list_response`, `standard_error`. |
| Repository/API/event surfaces | `OperationalLogRepository.write_summary`, `HealthRepository.write_observation`, metrics middleware. |
| Expected tests | Metric naming/unit tests, no-secret log tests, API latency metric tests, summary query tests. |
| Evidence artifacts | metrics scrape sample, pytest output, log redaction evidence. |
| Rollback notes | Revert observability modules and clear summary rows if required. |

### WP-13 Sphinx Documentation Build

| Field | Content |
|---|---|
| Goal | Make Sphinx build part of verification, first static docs and then autodoc after runtime modules exist. |
| Requirement IDs | SL-DECOMP-009, SL-REQ-004, V-SL-SPHINX-001 |
| Target files/modules | `docs/conf.py`, `docs/index.rst`, `docs/sphinx_build.md`, `tools/verify_sphinx_build.py`, future autodoc pages. |
| Schemas used | None directly. |
| Repository/API/event surfaces | Future autodoc surfaces for public modules, routes, workers, producers, consumers, validators, and retry handlers. |
| Expected tests | `python tools/verify_sphinx_build.py --docs-dir docs --output-file docs/verification/evidence/sphinx_build.txt`. |
| Evidence artifacts | Sphinx build output and generated HTML path. |
| Rollback notes | Revert Sphinx docs and generated evidence; remove `_build` if committed accidentally. |

### WP-14 End-to-End Demo Flow and Release Evidence

| Field | Content |
|---|---|
| Goal | Prove the complete demo flow from folder configuration through output delivery and dashboard visibility. |
| Requirement IDs | SL-LIFE-001 through SL-LIFE-020, SL-VER-001 through SL-VER-030, all implemented capability requirements. |
| Target files/modules | `tests/e2e/`, Docker Compose smoke scripts, evidence docs. |
| Schemas used | All event, API, and artifact schemas touched by the demo flow. |
| Repository/API/event surfaces | All production surfaces. |
| Expected tests | Docker Compose smoke, E2E valid file flow, validation failure quarantine flow, retry/exhaustion flow, dashboard manual checks. |
| Evidence artifacts | `docs/verification/evidence/e2e_demo_run.md`, command logs, screenshots if manual UI evidence is required. |
| Rollback notes | Stop Compose, reset volumes, clean source/destination/quarantine folders. |

## Definition of Done for a Codex Work Package

A work package is done only when:

1. All listed requirement IDs are either implemented or explicitly deferred with a documented reason.
2. Contract lint passes.
3. JSON Schema fixture validation passes for touched schemas.
4. Unit/integration tests for the package pass.
5. Required verification/evidence artifacts are updated.
6. Worklog is added under `docs/worklogs/`.
7. No undocumented env vars, routes, metrics, schemas, states, or events were introduced.
8. Rollback notes identify both code rollback and demo-state cleanup.
