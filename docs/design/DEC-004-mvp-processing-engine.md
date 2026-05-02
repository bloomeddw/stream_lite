# DEC-004: MVP Processing Engine

## Status

Accepted for v0.1.

## Decision

Stream Lite v0.1 shall implement and verify Apache Spark as the default and only active processing engine. Flink remains future-compatible scope and shall not be accepted by v0.1 runtime configuration.

## Rationale

The demo is file-drop oriented and batch-like. Spark is easier to explain, verify, and operate for local file fixtures. Keeping the processing contract engine-neutral preserves future Flink extensibility without requiring unverified Flink runtime behavior now.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Spark only | Good fit for file transformation, simpler local POC, clear fixture verification. | Does not demonstrate continuous stream processing. |
| Flink only | Strong fit for streaming semantics. | Heavier conceptual and operational scope for file-drop demo. |
| Both engines | Demonstrates abstraction. | Doubles runtime and verification burden. |

## Requirement Impact

- `REQ-001` accepts `STREAM_LITE_PROCESSING_ENGINE=spark` only for v0.1.
- `REQ-007` requires Spark processing and defers Flink activation.

## Verification Impact

Acceptance tests target Spark processing for CSV, JSON, and text fixtures. Flink tests are deferred until a later decision activates Flink.
