# REQ-013: Security and Path Safety Requirements

## Capability Intent

The local proof-of-concept shall prevent unsafe filesystem access, accidental path traversal, destructive operations outside configured mounts, and arbitrary code execution from operator input.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-SEC-001 | The system shall maintain an allowlist of mounted source roots. | Must | V-SL-SEC-001 |
| SL-SEC-002 | The system shall maintain an allowlist of mounted destination roots. | Must | V-SL-SEC-002 |
| SL-SEC-003 | Watcher creation shall reject paths outside the configured source root allowlist. | Must | V-SL-SEC-003 |
| SL-SEC-004 | Watcher creation shall reject destinations outside the configured destination root allowlist. | Must | V-SL-SEC-004 |
| SL-SEC-005 | Path normalization shall resolve `.`, `..`, duplicate separators, symlinks where exposed, and relative paths before allowlist checks; policy checks shall use the resolved absolute container path. | Must | V-SL-SEC-005 |
| SL-SEC-006 | The system shall reject path traversal attempts such as `../` escaping mounted roots. | Must | V-SL-SEC-006 |
| SL-SEC-007 | The dashboard shall not allow arbitrary shell command execution. | Must | V-SL-SEC-007 |
| SL-SEC-008 | The API shall not accept arbitrary Spark or Flink code from users in v0.1. | Must | V-SL-SEC-008 |
| SL-SEC-009 | Error responses shall not expose host-only absolute paths; debug mode may include container paths only when `STREAM_LITE_DEBUG=true` and shall still redact secrets. | Must | V-SL-SEC-009 |
| SL-SEC-010 | Secrets and passwords shall be supplied through environment variables, not hardcoded in source. | Must | V-SL-SEC-010 |
| SL-SEC-011 | Application containers for API, dashboard, watcher, and worker shall run as non-root users unless a documented Docker image constraint prevents it; any exception shall be listed in `docs/operations/docker_compose.md`. | Must | V-SL-SEC-011 |
| SL-SEC-012 | API mutation endpoints shall be prepared for authentication integration even if v0.1 runs in local trusted mode. | Could | V-SL-SEC-012 |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-SEC-NFR-001 | Path traversal fixture rejection | 100% |
| SL-SEC-NFR-002 | Outside-mount path rejection | 100% |
| SL-SEC-NFR-003 | Hardcoded secret scan of repository | 0 known secrets |
| SL-SEC-NFR-004 | Arbitrary code execution routes exposed from dashboard | 0 |
| SL-SEC-NFR-005 | Destructive source-file operations during detection/validation | 0 |

## L2 Contract Decomposition Requirements

These rows decompose local-demo security into allowlist, normalization, trusted-mode boundary, secret handling, and container-user contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-SEC-013 | L2 | SL-SEC-001, SL-SEC-002, SL-SEC-003, SL-SEC-004 | Path allowlist contract | Source and destination path checks shall compare resolved container paths against configured allowlists before persistence, scan, validation, processing, delivery, or dashboard display. | Must | V-SL-SEC-013 |
| SL-SEC-014 | L2 | SL-SEC-005, SL-SEC-006, SL-SEC-009 | Path normalization and message contract | Path normalization shall resolve relative segments, duplicate separators, and exposed symlinks; rejected paths shall return a documented code and no host-only absolute path. | Must | V-SL-SEC-014 |
| SL-SEC-015 | L2 | SL-SEC-007, SL-SEC-008, SL-SEC-012 | Local trusted mode boundary contract | v0.1 local trusted mode may allow unauthenticated local API/dashboard use but shall not expose arbitrary shell execution, arbitrary processing code submission, or remote-auth assumptions. | Must | V-SL-SEC-015 |
| SL-SEC-016 | L2 | SL-SEC-010 | Secret handling contract | Secrets shall be read only from documented environment variables, redacted from logs/responses, excluded from schema examples, and never stored in requirements, worklogs, or evidence. | Must | V-SL-SEC-016 |
| SL-SEC-017 | L2 | SL-SEC-011 | Container user contract | API, dashboard, watcher, and worker containers shall run as non-root users or document service-specific image constraint, risk, and rollback path. | Must | V-SL-SEC-017 |

## Acceptance Criteria

The requirement is accepted when path safety tests reject traversal and outside-mount paths, the dashboard cannot submit arbitrary executable code, and no source file is deleted or modified during detection, validation, processing, or failed delivery.

## Path Safety Error Codes

| Code | Trigger | HTTP status |
|---|---|---:|
| `PATH_NOT_ALLOWLISTED` | Resolved path is outside configured source or destination roots. | 422 |
| `PATH_TRAVERSAL_REJECTED` | Raw path attempts traversal outside mounted root. | 422 |
| `PATH_NOT_FOUND` | Resolved path does not exist when existence is required. | 422 |
| `PATH_NOT_DIRECTORY` | Resolved path is not a directory for watcher source/destination configuration. | 422 |
| `PATH_NOT_READABLE` | Source directory cannot be read by service user. | 422 |
| `PATH_NOT_WRITABLE` | Destination directory cannot be written by service user. | 422 |
| `PATH_SYMLINK_ESCAPE` | Symlink resolution escapes allowed root. | 422 |

## Operator-Safe Message Definition

An operator-safe message shall include a stable error or reason code, the affected resource role, and a sanitized display path when useful. It shall exclude secrets, passwords, tokens, host-only absolute paths, raw stack traces, and unredacted environment variable values. If a full path is needed for local debugging, it shall be shown only when `STREAM_LITE_DEBUG=true` and shall use the container path after allowlist checks.
