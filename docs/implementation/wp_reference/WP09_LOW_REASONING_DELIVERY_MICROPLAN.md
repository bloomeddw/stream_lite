# WP-09 Low-Reasoning Delivery Microplan

**Status:** Codex handoff reducer for WP-09  
**Scope:** Documentation-only implementation map. This is not a prompt by itself.  
**Purpose:** Split WP-09 into two bounded implementation runs so Codex does not need to reason through routing, filesystem copy, manifest schema, worker state transitions, repositories, and events in one pass.

## Safety invariants for both WP09-A and WP09-B

These invariants are mandatory and apply to every WP-09 subtask:

1. Read `AGENTS.md` and `RULES.md` first.
2. Do not create or reference `.codex/` files or folders.
3. Do not create `CODEX_DESTRUCTIVE_OPERATION_RULES.md`.
4. Do not delete files from the working tree as cleanup.
5. Do not run `Remove-Item -Recurse`, `rm -rf`, `git clean`, `git reset --hard`, `rd /s`, `rmdir /s`, `del /s`, `find -delete`, or repo-root cleanup loops.
6. Do not delete `.venv/`, `docs/_build/`, `.pytest_cache/`, `__pycache__/`, `*.pyc`, `tmp/`, `.tmp/`, `pytest_vendor/`, `.pytest_vendor/`, or `wheelhouse/`.
7. Package by explicit include list only; exclude generated/cache/vendor artifacts from the zip instead of deleting them.
8. Stop before coding if the current repository state conflicts with this microplan, the WP-09 reference, schemas, or requirements.

## Fixed WP-09 package split

WP-09 SHALL be implemented in two runs:

| Run | Name | Implements | Must not implement |
|---|---|---|---|
| WP09-A | Delivery routing, filesystem copy, and output-manifest contract helpers | `app/delivery/__init__.py`, `app/delivery/routing.py`, `app/delivery/filesystem.py`, manifest model/schema/example alignment, routing/filesystem/manifest tests | `app/delivery/service.py`, job state transitions, stage claims, outbox events, retry decisions, WP-10 |
| WP09-B | DeliveryWorker repository/state/event integration | `app/delivery/service.py`, worker tests, event enqueues, delivery attempts, state transitions, final verification | Schema redesign beyond gaps discovered in WP09-A, watcher/validation/processing changes, WP-10 |

## Required reference reads

### WP09-A reads

Read only these files before coding WP09-A unless a failing test points to a specific dependency:

- `AGENTS.md`
- `RULES.md`
- `rtc_source.md`, if present
- `docs/implementation/CODEX_TASK_GUIDE.md`
- `docs/implementation/wp_reference/WP09_DELIVERY_REFERENCE.md`
- `docs/reqs/REQ-008-output-delivery.md`
- `docs/reqs/REQ-013-security-and-path-safety.md`
- `docs/reqs/REQ-016-data-contracts-and-schema-governance.md`
- `docs/design/DEC-001-tag-based-folder-routing.md`
- `docs/schemas/artifact_schemas.md`
- `docs/verification/verification_matrix.md`
- `app/config/path_policy.py`
- `app/watcher/routing.py`
- `app/artifacts/models.py`
- `schemas/artifacts/output_manifest.schema.json`
- `schemas/examples/artifacts/output_manifest.valid.json`

### WP09-B reads

Read only these files before coding WP09-B unless a failing test points to a specific dependency:

- all WP09-A changed files and tests
- `AGENTS.md`
- `RULES.md`
- `docs/implementation/wp_reference/WP09_DELIVERY_REFERENCE.md`
- `docs/reqs/REQ-005-event-streaming.md`
- `docs/reqs/REQ-006-job-metadata-and-state.md`
- `docs/reqs/REQ-008-output-delivery.md`
- `docs/reqs/REQ-012-operational-logging-and-observability.md`
- `docs/reqs/REQ-017-end-to-end-lifecycle-and-handoff-orchestration.md`
- `app/repositories/delivery.py`
- `app/repositories/jobs.py`
- `app/repositories/stage_claims.py`
- `app/repositories/watchers.py`
- `app/events/outbox.py`
- `app/events/models.py`
- `app/processing/engine.py`
- `schemas/events/delivery_started.schema.json`
- `schemas/events/delivery_completed.schema.json`
- `schemas/events/delivery_failed.schema.json`
- `schemas/events/job_completed.schema.json`

## WP09-A exact build instructions

### Files to create or update

Create:

- `app/delivery/__init__.py`
- `app/delivery/routing.py`
- `app/delivery/filesystem.py`
- `tests/delivery/test_delivery_routing.py`
- `tests/delivery/test_delivery_filesystem.py`
- `tests/delivery/test_output_manifest.py`
- `docs/worklogs/WORKLOG-<date>-wp09a-delivery-routing-filesystem-manifest.md`

Update only if the existing contract rejects required WP-09 destination outcomes:

- `app/artifacts/models.py`
- `schemas/artifacts/output_manifest.schema.json`
- `schemas/examples/artifacts/output_manifest.valid.json`
- `docs/schemas/artifact_schemas.md`
- `docs/worklogs/INDEX.md`

Do not create `app/delivery/service.py` in WP09-A.

### `app/delivery/routing.py`

Implement pure helpers only; no database writes.

Use `app.watcher.routing.normalize_route_tags` and the same matching semantics as WP-06.

Create:

```python
@dataclass(frozen=True)
class DeliveryTarget:
    destination_folder_id: UUID
    destination_container_locator: str
    destination_display_path: str
    destination_route_tags: tuple[str, ...]
    matched_route_tags: tuple[str, ...]

@dataclass(frozen=True)
class DeliveryRouteResolution:
    targets: tuple[DeliveryTarget, ...]
    unmatched_reason: str | None
```

Implement:

```python
def resolve_delivery_targets(source_route_tags: Sequence[str], watcher_destinations: Sequence[Any]) -> DeliveryRouteResolution:
    ...
```

Destination objects used by tests may be dataclasses with these attributes:

- `id` or `destination_folder_id`
- `path` or `destination_container_locator`
- `display_path` or `destination_display_path`
- `route_tags`

Behavior:

- Normalize source tags and destination tags.
- Match every destination with non-empty tag intersection.
- Return deterministic target order matching input destination order.
- Return `unmatched_reason="NO_MATCHING_DESTINATION"` when no targets match.
- Do not infer tags from repositories in WP09-A.

### `app/delivery/filesystem.py`

Create dataclasses:

```python
@dataclass(frozen=True)
class DeliveryCopyResult:
    status: Literal["delivered", "failed"]
    finalized_locator: str | None
    finalized_display_path: str | None
    checksum_sha256: str | None
    bytes_written: int
    reason_code: str | None
    retryable: bool
    operator_message: str
```

Implement:

```python
def copy_output_to_destination(
    *,
    source_output_locator: str,
    destination_root_locator: str,
    watcher_id: UUID,
    job_id: UUID,
    as_of_date: date,
    filesystem_resolver: Callable[[str], Path] = Path,
    path_policy: PathPolicy | None = None,
) -> DeliveryCopyResult:
    ...
```

Destination layout:

```text
<destination_root>/watcher_id=<watcher_id>/date=YYYY-MM-DD/job_id=<job_id>/output.<extension>
```

Copy rules:

- Validate destination root through `PathPolicy` when provided.
- Resolve only for local filesystem access; persist/report POSIX container locators only.
- If source missing: `SOURCE_TRANSFER_FAILED`, retryable `true`.
- If destination root missing: `DESTINATION_NOT_FOUND`, retryable `true`.
- If destination root not allowlisted: `DESTINATION_NOT_ALLOWLISTED`, retryable `false`.
- Write to a temporary file under the same destination directory.
- Verify byte count and SHA-256 after writing.
- Finalize with `Path.replace` for same-filesystem atomic rename.
- If replace unsupported: `FINALIZE_UNSUPPORTED`, retryable `false`.
- If replace fails: `FINALIZE_FAILED`, retryable `true`.
- Never delete source output.
- Never expose host paths in result fields.

### Output manifest contract closure

WP-08 writes processed manifests with `status="processed"` and `destination_outcomes=[]`.

WP09-A must ensure `OutputManifest` schema/model/examples accept final statuses:

- `delivered`
- `completed_with_delivery_errors`
- `failed`

Each destination outcome must validate with these fields:

```json
{
  "destination_folder_id": "uuid",
  "destination_display_path": "/dest/orders",
  "matched_route_tags": ["ORDERS"],
  "status": "delivered|failed|skipped",
  "finalized_locator": "/stream-lite-test/destinations/orders/watcher_id=.../date=.../job_id=.../output.csv",
  "checksum_sha256": "64 lowercase hex chars",
  "bytes_written": 123,
  "reason_code": null,
  "retryable": null
}
```

For failed/skipped outcomes, `finalized_locator`, `checksum_sha256`, and `bytes_written` may be `null`, while `reason_code` and `retryable` are required.

Do not add worker-only fields or event logic in WP09-A.

### WP09-A tests

Add tests for:

- one source routes to one destination
- one source routes to multiple destinations
- zero matches returns `NO_MATCHING_DESTINATION`
- successful atomic copy writes final output and leaves source unchanged
- copied byte count and SHA-256 are correct
- missing source returns `SOURCE_TRANSFER_FAILED`
- missing destination returns `DESTINATION_NOT_FOUND`
- outside-allowlist destination returns `DESTINATION_NOT_ALLOWLISTED`
- result locators do not include Windows host paths or pytest temp paths
- final delivered, partial, and failed output manifests validate against Pydantic model and JSON schema

Use container locators like:

```text
/stream-lite-test/processing/job_id=<job_id>/output/orders.csv
/stream-lite-test/destinations/orders
```

Use `tmp_path` only behind `filesystem_resolver`.

### WP09-A verification

Run:

```powershell
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
pytest tests/delivery/test_delivery_routing.py tests/delivery/test_delivery_filesystem.py tests/delivery/test_output_manifest.py
```

Do not run full `pytest tests` in WP09-A unless the targeted tests pass first.

### WP09-A final response

Report:

1. Scope
2. Files changed
3. Schema/model changes
4. Tests run with exact results
5. Gaps
6. Final verdict: WP09-A ready for WP09-B or blocked

## WP09-B exact build instructions

Start WP09-B only after WP09-A targeted tests pass.

### Files to create or update

Create:

- `app/delivery/service.py`
- `tests/delivery/test_delivery_service.py`
- `docs/worklogs/WORKLOG-<date>-wp09b-delivery-worker.md`

Update as needed:

- `docs/worklogs/INDEX.md`
- event examples/docs only if schemas require example changes

Do not modify routing/filesystem behavior unless a WP09-B test proves a gap.

### DeliveryWorker contract

Create:

```python
class DeliveryWorker:
    def deliver_one(self, job_id: UUID, correlation_id: str | None = None) -> DeliveryWorkerResult: ...
    def claim_and_deliver(self, limit: int = 1, correlation_id: str | None = None) -> DeliveryBatchResult: ...
```

Use constructor injection for repositories and helpers. Mirror WP-08 `ProcessingWorker` dependency style.

### `deliver_one` state machine

Implement exactly:

1. Load job.
2. If missing: return skipped `JOB_NOT_FOUND`; no side effects.
3. If state is not `PROCESSED`: return skipped `JOB_NOT_DELIVERABLE`; no side effects.
4. Load latest processed output manifest for the job.
5. If missing: return skipped or failed `OUTPUT_MANIFEST_NOT_FOUND`; no copy/events.
6. Resolve destinations using WP09-A routing helper.
7. If no destinations:
   - transition `PROCESSED -> FAILED`
   - set latest error code `NO_MATCHING_DESTINATION`
   - append state history
   - release/avoid claim as appropriate
8. Claim stage:
   - `stage="delivery"`
   - `owner_service="delivery"`
   - `attempt_number=job.attempt_number`
   - lease seconds = 30
9. Transition `PROCESSED -> DELIVERING`; append state history.
10. For each target:
    - create delivery attempt pending/started
    - enqueue `delivery.started`
    - copy through WP09-A filesystem helper
    - complete/fail attempt
    - enqueue `delivery.completed` or `delivery.failed`
11. Determine final state:
    - all delivered: `DELIVERING -> DELIVERED -> COMPLETED`
    - mixed success/failure: `DELIVERING -> COMPLETED_WITH_DELIVERY_ERRORS`
    - all failed retryable with attempts remaining: `DELIVERING -> RETRY_PENDING`
    - all failed not retryable or exhausted: `DELIVERING -> FAILED`
12. Write final output manifest with destination outcomes.
13. Persist output manifest row/reference with `DeliveryRepository.create_output_manifest`.
14. Enqueue `job.completed` only for `COMPLETED` and `COMPLETED_WITH_DELIVERY_ERRORS`.
15. Release stage claim in every path after claim acquisition.
16. Do not schedule retry and do not start WP-10.

### Event contracts

Use:

- stream: `stream_lite.lifecycle`
- producer: `delivery`
- schema_version: `1.0.0`

Payload fields must match existing event schemas exactly. Inspect schemas before constructing payloads. Do not invent fields.

Idempotency key shape:

```text
<event_type>:<job_id>:<destination_folder_id or job>:<attempt_number>
```

### WP09-B tests

Add tests for:

- one destination success: `PROCESSED -> DELIVERING -> DELIVERED -> COMPLETED`
- delivery attempt created and completed
- `delivery.started`, `delivery.completed`, and `job.completed` enqueued
- output manifest row persisted
- multi-destination all success creates one attempt per destination
- partial failure transitions to `COMPLETED_WITH_DELIVERY_ERRORS`
- all failure does not transition to `COMPLETED`
- non-`PROCESSED` job is skipped with no side effects
- claim conflict prevents copy/events/state changes
- claim released on success and failure
- worker does not schedule retry
- no host paths in DB rows, artifact, or logs

### WP09-B verification

Run:

```powershell
python -S tools/contract_lint.py --write-inventory
python tools/validate_schema_examples.py --write-evidence
python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt
pytest tests/delivery
pytest tests/processing
pytest tests/validation
pytest tests/watcher
pytest tests/events
pytest tests/repositories
pytest tests/config tests/api tests/observability
pytest tests/schemas
pytest tests/db
pytest tests/contract
pytest tests
```

### WP09-B final response

Report:

1. Scope
2. Safety rules followed
3. Requirements implemented
4. Files changed
5. Contract/schema changes
6. Tests run with exact results
7. Evidence artifacts updated
8. Assumptions
9. Gaps
10. Rollback notes
11. Final verdict: WP-09 ready for WP-10 or blocked

## Stop conditions

Stop and report instead of coding when:

- Any required existing repository method is absent and adding it would require a migration.
- Event schemas reject the required WP09-B payload shape and the fix is not a narrow example/model alignment.
- Output manifest schema conflicts with WP-08 processed manifests.
- PathPolicy cannot validate destination roots without a new env var.
- A proposed command would delete or reset files in the working tree.

## Expected reasoning reduction

This split removes multi-destination filesystem correctness, manifest schema closure, repository stage claims, state transitions, and outbox event payload reasoning from the same Codex pass. WP09-A should be a low-reasoning implementation task. WP09-B should be moderate but bounded because routing, copy behavior, and final manifest validation will already be settled.
