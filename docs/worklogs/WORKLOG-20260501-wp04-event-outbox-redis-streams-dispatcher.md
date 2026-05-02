# WORKLOG-20260501-wp04-event-outbox-redis-streams-dispatcher

## Summary

Implemented WP-04 only. WP-05 was not started. The patch adds schema-validated event outbox enqueueing, a Redis Streams publication wrapper, callable dispatcher primitives for pending outbox publication, bounded publish retry handling, third-failure dead-letter behavior, and API-safe event listing support backed by persisted outbox rows.

The active lifecycle stream is `stream_lite.lifecycle`. The dead-letter stream is `stream_lite.dead_letter`. Domain-specific split streams `stream_lite.jobs`, `stream_lite.files`, `stream_lite.delivery`, and `stream_lite.commands` remain deferred future scope and were not implemented.

Event enqueue validates with WP-02 Pydantic event models. The dispatcher publishes pending outbox rows and updates outbox status. Dead-letter behavior is implemented for the third publish failure. Redis interactions are tested with a fake or injected client; a real Redis service was not required or assumed to be available.

No new env vars were added. No database migrations were added because no schema mismatch required one.

## Files Changed

- `requirements.txt`
- `app/events/__init__.py`
- `app/events/outbox.py`
- `app/events/redis_streams.py`
- `app/events/dispatcher.py`
- `app/repositories/events.py`
- `tests/events/test_outbox.py`
- `tests/events/test_redis_streams.py`
- `tests/events/test_dispatcher.py`
- `tests/events/test_event_listing.py`

## Requirements Affected

- `SL-EVT-001` through `SL-EVT-026`
- `SL-JOB-048`
- `SL-JOB-049`
- `SL-LIFE-010`
- `SL-LIFE-011`
- `SL-OBS-006`
- `SL-DCT-001` through `SL-DCT-033` where schema-bound validation and example parity are reused

## Contract/Schema Usage

- `docs/design/DEC-010-event-stream-naming.md`
- `docs/reqs/REQ-005-event-streaming.md`
- `docs/reqs/REQ-006-job-metadata-and-state.md`
- `docs/reqs/REQ-012-operational-logging-and-observability.md`
- `docs/operations/environment_variables.md`
- `docs/schemas/events.md`
- `schemas/events/*.schema.json`
- `schemas/examples/events/*.json`
- `schemas/api/event_list_response.schema.json`
- `app/events/models.py`

## Decisions Applied

- Used `stream_lite.lifecycle` as the default active lifecycle stream for WP-04 enqueue and dispatch.
- Used `stream_lite.dead_letter` only for dead-letter payload publication after the third publish failure.
- Preserved deferred future scope for domain-specific split streams; no per-domain routing was added.
- Kept event schema validation authoritative through WP-02 Pydantic event models and schema fixtures instead of adding custom payload contracts.
- Kept Redis connection/publication logic separate from dispatcher logic and allowed fake client injection for tests.
- Kept `event_offsets` consumer-owned. Dispatcher publication does not write consumer offsets because the current docs assign `event_offsets` to event consumers rather than the outbox dispatcher.
- Used the documented deterministic WP-04 publish backoff only: first failure `+1s`, second failure `+2s`, third failure dead-letter.
- Added no new metrics, tables, routes, retries, state transitions, env vars, or migrations.

## Verification Commands/Results

- `python -S tools/contract_lint.py --write-inventory`
  Result: passed
- `python tools/validate_schema_examples.py --write-evidence`
  Result: passed, `169` examples validated
- `python tools/verify_sphinx_build.py --docs-dir docs --build-dir docs/_build/html --output-file docs/verification/evidence/sphinx_build.txt`
  Result: Sphinx build exit code `0`
- `pytest tests/contract`
  Result: `3 passed`
- `pytest tests/config tests/api tests/observability`
  Result: `16 passed`
- `pytest tests/schemas`
  Result: `213 passed`
- `pytest tests/db tests/repositories`
  Result: `9 passed`
- `pytest tests/events`
  Result: `8 passed`

## Assumptions

- Dead-letter records are published directly to `stream_lite.dead_letter` and are not persisted as separate outbox rows because the active contract documents dead-letter payload fields but does not define a separate dead-letter event schema or outbox row type for WP-04.
- Dispatcher-side publish exceptions default to `BROKER_UNAVAILABLE` when an exception does not already expose a documented `error_code`.
- Final route-layer response shaping for `GET /events` remains a later package concern; WP-04 only provides repository and service primitives for persisted summaries.

## Gaps

- No real Redis integration test was added because WP-04 explicitly allows fake or injected Redis clients and no real Redis service was assumed to exist in this environment.
- Dispatcher reconciliation loops, workers, validators, processors, delivery workers, retry schedulers, and FastAPI route handlers remain out of scope for this patch.
- Consumer offset writes remain deferred to future consumer work packages because WP-04 does not yet add consumers.

## Rollback Notes

- Revert `requirements.txt`, `app/events/`, `app/repositories/events.py`, and `tests/events/`.
- No database rollback is required because no migration or schema change was added.
- Demo/runtime cleanup after rollback is limited to clearing Redis stream data for `stream_lite.lifecycle` and `stream_lite.dead_letter` if any manual publish tests were run outside unit tests.

## Next Step

Keep WP-05 blocked until this WP-04 patch is accepted. The next package can build documented `GET /events` route behavior on top of the new persisted event listing primitives without reading Redis Streams directly.
