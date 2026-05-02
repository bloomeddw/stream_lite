# Delete Manifest: Remove Former Separate Decomposition Requirement

Date: 2026-04-25

## Files to delete from active baseline

- `stream_lite/docs/reqs/REQ-018-contract-decomposition-and-implementation-readiness.md`

## Reason

The separate decomposition gate was removed because implementation-facing decomposition belongs in the owning capability requirements and supporting contract artifacts. Active requirement numbering now ends at `REQ-017`; the decomposed contract artifacts are traced to `REQ-004`, `REQ-005`, `REQ-006`, `REQ-008`, `REQ-009`, `REQ-010`, `REQ-011`, `REQ-012`, `REQ-014`, `REQ-016`, and `REQ-017`.
