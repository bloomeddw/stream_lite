# DEC-005: Quarantine File Handling

## Status

Accepted for v0.1.

## Decision

Invalid files shall be copied to the configured quarantine root. Stream Lite shall not delete, move, rename, or modify the original source file during quarantine handling.

## Rationale

Copy-based quarantine preserves operator trust, enables repeatable demo verification, and keeps path-safety behavior straightforward. It also avoids destructive side effects in a local demo where source folders may contain user-provided files.

## Requirement Impact

- `REQ-004` requires quarantine records and copy behavior.
- `REQ-013` and `REQ-015` prohibit destructive source-file operations.

## Verification Impact

Quarantine verification shall prove the quarantine copy exists, the original source file remains unchanged, reason codes are persisted, and `file.quarantined` is emitted.
