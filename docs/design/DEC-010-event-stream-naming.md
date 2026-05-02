# DEC-010: Event Stream Naming

## Status

Accepted for v0.1 contract baseline.

## Context

Before WP-04, the event schema inventory and API event-list model converged on a single lifecycle stream named `stream_lite.lifecycle` for active lifecycle events. `REQ-005` still described an older multi-stream MVP split across `stream_lite.jobs`, `stream_lite.files`, `stream_lite.delivery`, `stream_lite.commands`, and `stream_lite.dead_letter`. That mismatch would force the event dispatcher to choose between conflicting contracts.

WP-04 shall not implement Redis publication until the stream naming contract is unambiguous.

## Options Considered

### Option 1: Single lifecycle stream plus dead-letter stream

All active v0.1 lifecycle events publish to `stream_lite.lifecycle`. Failed consumer records publish to `stream_lite.dead_letter` after dead-letter criteria are met.

Pros:

- Aligns with `docs/schemas/events.md`, API event-list schema expectations, examples, and the current `EventListItem.stream_name` contract.
- Keeps local-demo Redis Streams operation simpler.
- Reduces dispatcher routing logic before worker behavior exists.
- Makes `GET /events` and persisted outbox listing easier to verify against one active lifecycle stream.

Cons:

- Does not separate jobs, files, delivery, and commands into independent Redis streams in v0.1.
- A future production-like domain split will require a compatibility decision and coordinated schema/API/consumer updates.

### Option 2: Multiple domain streams plus dead-letter stream

Lifecycle events are partitioned across `stream_lite.jobs`, `stream_lite.files`, `stream_lite.delivery`, and `stream_lite.commands`, with `stream_lite.dead_letter` for failures.

Pros:

- More closely resembles a domain-partitioned event topology.
- Allows future consumer groups to subscribe to narrower streams.

Cons:

- Conflicts with the current event schema inventory, event-list API model, and examples.
- Adds dispatcher routing complexity before the demo has worker implementations.
- Requires additional tests and migration notes for stream offsets and per-stream retention.

## Decision

Stream Lite v0.1 shall use:

- `stream_lite.lifecycle` for active lifecycle events.
- `stream_lite.dead_letter` for dead-letter records.

The older domain-specific streams `stream_lite.jobs`, `stream_lite.files`, `stream_lite.delivery`, and `stream_lite.commands` are deferred future scope. They shall not be implemented in WP-04 unless a later accepted decision updates requirements, schema inventory, examples, API models, consumers, stream offsets, operations docs, and tests together.

## Rationale

This decision aligns the event-streaming requirement with the already active schema inventory, API event list schema, examples, and local-demo operations model. It keeps WP-04 focused on the outbox-to-Redis dispatcher contract instead of introducing a new routing architecture.

## Impacts

### Requirements

- Updates `REQ-005` so the v0.1 stream contract names `stream_lite.lifecycle` and `stream_lite.dead_letter` explicitly.
- Preserves dead-letter behavior after three failed consumer handling attempts.
- Defers domain-specific stream partitioning to future scope.

### WP-04 Implementation

- The dispatcher shall publish active lifecycle events from the outbox to `stream_lite.lifecycle`.
- Dead-letter records shall be written to `stream_lite.dead_letter` only after the documented failure threshold is met.
- The dispatcher shall not invent per-domain routing during WP-04.

### Tests

- WP-04 tests shall verify lifecycle stream publication uses `stream_lite.lifecycle`.
- WP-04 tests shall verify dead-letter records target `stream_lite.dead_letter` and include the documented dead-letter fields.
- Tests for `stream_lite.jobs`, `stream_lite.files`, `stream_lite.delivery`, and `stream_lite.commands` are deferred until domain stream partitioning is activated.

### Operations

- Local Redis Streams troubleshooting shall inspect `stream_lite.lifecycle` and `stream_lite.dead_letter` for v0.1.
- Future operations docs may add domain-specific stream guidance only after a later decision activates that topology.

### Maintainability

- A single lifecycle stream reduces MVP complexity and makes the event contract easier to reason about.
- Deferred domain streams remain a reversible architectural option because event payloads retain event type, producer, job ID, watcher ID, and correlation ID.

## Deferred Enhancement

Domain-specific streams may be introduced later to split lifecycle traffic by domain. That enhancement shall include a new decision or update to this one, schema/API compatibility notes, event offset migration guidance, consumer routing tests, and updated operations docs.
