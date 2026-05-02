# DEC-006: Manual Retry Eligibility

## Status

Accepted for v0.1.

## Decision

Manual retry is allowed for eligible failed processing and delivery jobs. Manual retry is not allowed for validation-policy quarantine failures such as unsupported extension, invalid schema, path policy violation, oversized file, empty file, or duplicate file.

## Rationale

Processing and delivery failures often reflect transient infrastructure or destination conditions. Validation-policy failures reflect deterministic input policy violations and should not be retried without a future edit/reprocess workflow.

## Requirement Impact

- `REQ-009` defines the manual retry eligibility contract.
- `REQ-010` returns `409 JOB_NOT_RETRYABLE` for blocked retries.
- `REQ-011` hides or disables retry controls for non-retryable failures.

## Verification Impact

Retry tests shall include accepted processing retry, accepted delivery retry, rejected validation quarantine retry, and rejected retry for non-terminal jobs.
