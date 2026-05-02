# DEC-003: MVP Broker Profile

## Status

Accepted for v0.1.

## Decision

Stream Lite v0.1 shall implement and verify Redis Streams as the only active event broker profile. Redpanda remains future-compatible scope and shall not be accepted by v0.1 runtime configuration.

## Rationale

Redis Streams minimizes local startup complexity and verification burden for the public Docker Compose demo while still supporting durable event coordination, consumer groups, and replay-oriented testing. This aligns the MVP with a requirements-first demonstration rather than expanding scope into multiple broker implementations before the default path is proven.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Redis Streams only | Fast local startup, easier testing, smaller runtime footprint. | Less Kafka-like production resemblance. |
| Redpanda only | Kafka-compatible semantics and stronger production story. | Heavier local stack and larger verification burden. |
| Both profiles | Demonstrates flexibility. | Doubles broker-specific requirements, tests, docs, and failure modes. |

## Requirement Impact

- `REQ-001` locks the active runtime profile to Redis Streams.
- `REQ-005` locks v0.1 event offsets to Redis Stream IDs.
- Redpanda selection fails with `CONFIG_UNSUPPORTED_DEFERRED_PROFILE` until a later accepted decision activates it.

## Verification Impact

Acceptance tests target Redis Streams startup, persistence, event append, consumer acknowledgement, idempotency, and replay. Redpanda tests are deferred.
