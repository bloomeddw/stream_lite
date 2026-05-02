# Batch Progress: Contract Hardening and Requirement Decomposition

## Batch 1 Completed

This batch addresses the highest-priority requirements-first cleanup items that could be completed without creating runtime implementation code or a full implementation plan.

### Completed in this patch

1. Confirmed `REQ-018` is absent from the submitted baseline and regenerated the requirement reference inventory with zero unresolved references and zero duplicate active requirement rows.
2. Added `tools/contract_lint.py` for static requirement/reference/schema/example/metric-unit checks.
3. Tightened API JSON schemas under `schemas/api/` from permissive placeholder fields to typed contracts with enums, UUID formats, timestamp patterns, path display contracts, pagination limits, and explicit object shapes.
4. Tightened event JSON schemas under `schemas/events/` with exact `event_type` constants, producer constants, envelope typing, UUID/timestamp contracts, attempt number contracts, and event-specific payload objects.
5. Added example fixtures under `schemas/examples/api/` and `schemas/examples/events/` as requested, rather than `tests/fixtures/`.
6. Standardized Prometheus duration metrics and API metric-summary duration fields on seconds using `_duration_seconds` and `stage_durations_seconds`.
7. Added `docs/data/migration_plan.md` to turn the logical model into migration-ready design guidance without creating Alembic code yet.
8. Added a static-first Sphinx skeleton: `docs/conf.py`, `docs/index.rst`, `docs/Makefile`, and `docs/sphinx_build.md`.
9. Expanded L3 implementation-surface traceability beyond API route handlers into watcher configuration, file detection, validation/quarantine, event outbox/dispatcher, processing, delivery, retry, Streamlit, and observability surfaces.
10. Added verification matrix rows for the new L3 and migration-design verification IDs.

### Explicitly not done per instruction

- No implementation plan was created.
- No runtime code, FastAPI app, workers, Streamlit pages, migrations, or processing code were created.

## Batch 2 Recommended Next

1. Run a focused schema-review pass on the tightened API/event schemas to make sure field names exactly match desired implementation names before generating Pydantic models.
2. Add invalid fixtures for every high-risk API and event schema, not only the first batch of invalid examples.
3. Add L3 persistence/repository decomposition for each migration table in `docs/data/migration_plan.md`.
4. Add endpoint/schema parity lint checks that compare `docs/api/endpoints.md`, `docs/schemas/api_schemas.md`, and `schemas/api/*.schema.json`.
5. Add event inventory/schema parity lint checks that compare `docs/schemas/events.md` and `schemas/events/*.schema.json`.
6. Add env-var and metrics-catalog parity lint checks.
7. Decide UUID generation ownership before creating Alembic scaffolding.

## Continue Prompt

Continue with Batch 2: schema-review, invalid fixture expansion, endpoint/event parity linting, env/metrics parity linting, and migration-table L3 persistence traceability. Do not create runtime implementation code or a full implementation plan yet.

## Batch 2 Completed: L2 Requirement Decomposition Alignment

This batch responds to the review finding that L3 traceability rows were added while several owning requirement files did not first define enough L2 contract requirements. It adds L2 contract decomposition across active requirement files that were still mostly L1 or L1-plus-L3.

### Completed in this patch

1. Added L2 contract decomposition to `REQ-001` for Docker Compose services, runtime configuration loading, volume ownership, service readiness, and unsupported runtime profiles.
2. Added L2 contract decomposition to `REQ-002` through `REQ-004` for watcher configuration/lifecycle/routing, file detection/stability/identity/deduplication/registration, and validation/quarantine outcomes.
3. Added L2 contract decomposition to `REQ-006` through `REQ-009` for job state, stage attempts, command/outbox durability, processing engine behavior, delivery fanout, and retry/manual retry/exhaustion behavior.
4. Added L2 contract decomposition to `REQ-011` through `REQ-017` for Streamlit API-backed controls, observability contracts, path safety, verification evidence, service boundaries, schema governance, and end-to-end handoff orchestration.
5. Added verification matrix rows for the new L2 verification IDs.
6. Regenerated `docs/reqs/REQUIREMENT_REFERENCE_INVENTORY.md` with zero unresolved requirement references and zero duplicate active requirement rows.

### Explicitly not done per instruction

- No implementation plan was created.
- No runtime implementation code, migrations, FastAPI routes, workers, or Streamlit pages were created.

## Batch 3 Recommended Next

1. Review the new L2 rows for terminology consistency and decide whether any L2 row should be split further before L3 repository/function traceability is expanded.
2. Add L3 persistence/repository decomposition for the durable tables in `docs/data/migration_plan.md` and `REQ-006`.
3. Add endpoint/schema parity lint checks for API contract documents and JSON schemas.
4. Add event inventory/schema parity lint checks for event docs and JSON schemas.
5. Add invalid examples under `schemas/examples` for high-risk API and event schemas.
6. Add env-var and metrics-catalog parity linting.

## Continue Prompt

Continue with Batch 3: review/split L2 rows where needed, add L3 persistence/repository traceability, and add contract parity linting for API, events, env vars, and metrics. Do not create runtime implementation code or a full implementation plan yet.

## Batch 2 Completion Gate Follow-up: Schema, Lint, and Persistence Readiness

This follow-up closes the checklist requested before moving to Batch 3.

### Completed in this patch

1. Completed schema field-name review before Pydantic generation and documented it in `docs/schemas/api_event_field_name_review.md`.
2. Renamed command response fields from `target_type`/`target_id` to `target_resource_type`/`target_resource_id` to align API schemas with command record contracts.
3. Added invalid fixtures for every active API schema and every active event schema under `schemas/examples`.
4. Expanded `tools/contract_lint.py` with endpoint/API schema parity checks, event inventory/schema parity checks, environment variable parity checks, and metrics catalog parity checks.
5. Fixed `.env.example` retry variable names to match requirements and the environment variable catalog.
6. Normalized stale metric references in `REQ-012` to the canonical `docs/operations/prometheus_metrics.md` names and the seconds duration convention.
7. Reviewed broad L2 schema-governance lint language and split it into specific L2 requirements for API schema parity, event schema parity, env-var parity, and metrics catalog parity.
8. Added L3 persistence/repository decomposition for every durable migration/logical-model table in `REQ-006` and linked each table in `docs/data/migration_plan.md`.
9. Decided UUID generation ownership through `docs/design/DEC-009-uuid-generation-ownership.md`: application-owned UUID generation for v0.1 before Alembic scaffolding.
10. Regenerated the requirement inventory with zero unresolved references and zero duplicate active rows.

### Verification performed

`python -S tools/contract_lint.py --write-inventory` passed.

### Still deferred by instruction

- No implementation plan was created.
- No runtime code, Alembic scaffolding, migrations, FastAPI routes, workers, or Streamlit pages were created.

## Batch 3 Recommended Next

1. Review the newly added L3 persistence rows for repository naming preferences before implementation planning.
2. Add deeper invalid fixtures for enum, timestamp, and path-safety failures beyond the current missing-required-field fixtures.
3. Add artifact schema parity linting for `schemas/artifacts` once output/quarantine/evidence fixture scope is finalized.
4. Continue decomposing any remaining L2 rows that feel too broad after review.
5. Prepare the implementation plan only after the requirements/contracts are accepted.

## Continue Prompt

Continue with Batch 3 after reviewing this Batch 2 completion patch. Do not create runtime implementation code unless explicitly instructed.

## Batch 4 Completed: Codex Task Guide and Verification Wiring

Batch 4 converts the requirements and contracts into ordered Codex work packages without writing runtime code.

### Completed in this patch

1. Added `docs/implementation/CODEX_TASK_GUIDE.md` with ordered work packages from contract validation through E2E verification.
2. Added target files/modules, requirement IDs, schemas used, repository/API/event surfaces, expected tests, evidence artifacts, and rollback notes for each work package.
3. Added `docs/implementation/naming_review.md` to freeze first-pass repository, route-handler, worker/service, module, metric-unit, UUID, and path/locator naming conventions before coding.
4. Added executable JSON Schema fixture validation wiring through `tools/validate_schema_examples.py` and `tests/contract/test_schema_examples.py`.
5. Added `requirements-dev.txt` for development-only verification dependencies: `jsonschema`, `pytest`, `sphinx`, and `myst-parser`.
6. Added Sphinx build verification wiring through `tools/verify_sphinx_build.py` and `tests/contract/test_sphinx_build_command.py`.
7. Updated `docs/sphinx_build.md` and `docs/index.rst` to include Batch 4 verification and implementation-readiness docs.
8. Added `docs/verification/evidence/README.md` to reserve generated evidence output locations.

### Verification performed

`python -S tools/contract_lint.py --write-inventory` passed.

JSON Schema execution was wired but not run in this container because development dependencies are not installed. The Sphinx verifier was run and produced skipped evidence because `sphinx-build` is not installed. Future verification command after installing `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/contract
```

### Explicitly not done per instruction

- No runtime implementation code was created.
- No Alembic migrations, FastAPI routes, workers, Streamlit pages, or processing code were created.

## Batch 5 Recommended Next

1. Install development dependencies and run the executable schema fixture validation plus Sphinx build verifier.
2. Fix any schema/example mismatches found by executable JSON Schema validation.
3. Review and approve the Codex task guide package order and naming map.
4. Start coding only after the implementation task guide is accepted.

## Continue Prompt

Continue with Batch 5: install/run verification dependencies if available, validate JSON Schema examples, run Sphinx build verification, and resolve any fixture/schema/doc issues before runtime implementation begins.

## Batch 5 Completed: Schema Fixture Validation Corrections and Local Environment Guidance

This follow-up responds to local executable JSON Schema validation failures reported after Batch 4.

### Completed in this patch

1. Corrected valid API fixtures that failed strict schema validation for uppercase error codes, semantic version strings, dependency health item count, and route tag format.
2. Corrected valid event fixtures that failed strict schema validation for uppercase error codes/reason codes, uppercase route tags, and deduplication key length.
3. Added `docs/implementation/development_environment.md` with virtual environment setup guidance and verification commands.
4. Linked the development environment guide from `docs/implementation/README.md` and the Sphinx index.
5. Regenerated requirement inventory through `tools/contract_lint.py` with zero unresolved references and zero duplicate active rows.

### Explicitly not done

- No runtime implementation code was created.
- No Alembic migrations, FastAPI routes, workers, Streamlit pages, or processing code were created.

### Continue Prompt

Rerun the executable verification commands inside an activated `.venv`: schema fixture validation, Sphinx build verification, and `pytest tests/contract`. If all pass, proceed to approve the Codex task guide or start the first implementation work package.
