# WP-06 Reference Map: Watcher Configuration, Routing, Detection, Stability, and Deduplication

## Purpose

Reduce Codex reasoning for WP-06 by fixing the expected watcher service boundaries, repository use, event outputs, and tests before implementation begins.

## Scope boundary

WP-06 implements watcher-side orchestration only: configuring watcher runtime state, route-tag matching, polling configured source folders, detecting candidate files, checking file stability, suppressing duplicates, registering jobs, and enqueueing watcher events.

WP-06 must not implement validation, quarantine, processing, delivery, retry scheduling, Streamlit pages, or new API routes.

## Primary requirement IDs

- `SL-FWM-001` through `SL-FWM-031`
- `SL-FDI-001` through `SL-FDI-029`
- `SL-JOB-035`
- `SL-JOB-036`
- `SL-LIFE-001` through `SL-LIFE-006`
- `SL-EVT-001`, `SL-EVT-002`, `SL-EVT-003`
- `SL-OBS-003`, `SL-OBS-006`
- `SL-SEC-001` through `SL-SEC-017` where paths are handled

## Read before coding

- `docs/reqs/REQ-002-folder-watch-management.md`
- `docs/reqs/REQ-003-file-detection-and-ingestion.md`
- `docs/reqs/REQ-005-event-streaming.md`
- `docs/reqs/REQ-006-job-metadata-and-state.md`
- `docs/reqs/REQ-017-end-to-end-lifecycle-and-handoff-orchestration.md`
- `docs/design/DEC-001-tag-based-folder-routing.md`
- `docs/operations/environment_variables.md`
- `app/config/path_policy.py`
- `app/repositories/watchers.py`
- `app/repositories/files.py`
- `app/repositories/jobs.py`
- `app/events/outbox.py`
- `app/events/models.py`
- `schemas/events/file_detected.schema.json`
- `schemas/events/file_stable.schema.json`
- `schemas/events/job_registered.schema.json`

## Target modules

| Module | Responsibility |
|---|---|
| `app/watcher/__init__.py` | Export WP-06 watcher surfaces only. |
| `app/watcher/routing.py` | Pure route-tag matching and preview logic. No filesystem access. |
| `app/watcher/stability.py` | File size/mtime stability check and SHA-256 calculation helpers. |
| `app/watcher/deduplication.py` | Duplicate suppression key creation and repository check/record calls. |
| `app/watcher/service.py` | Poll-once watcher orchestration; no long-running daemon required unless already scoped. |
| `tests/watcher/test_routing.py` | Tag matrix and fanout routing tests. |
| `tests/watcher/test_stability.py` | Stability window and SHA-256 tests using temp files. |
| `tests/watcher/test_deduplication.py` | Deduplication key and suppression repository tests. |
| `tests/watcher/test_service.py` | Poll-once happy path and safe-path rejection tests. |

## Fixed implementation map

### Route matching

Use the existing route policy `tag_match_all_destinations`.

A source matches a destination when the intersection of normalized route tags is non-empty. A source may match multiple destinations. Multiple sources may match one destination.

Create simple pure helpers:

- `normalize_route_tags(tags: list[str]) -> tuple[str, ...]`
- `match_source_to_destinations(source, destinations) -> list[destination]`
- `build_route_preview(sources, destinations) -> RoutePreviewResult`

Do not write database rows from pure routing helpers. Persist route preview/results only through repository methods when the watcher service explicitly needs to store them.

### File detection

The watcher service should operate as `poll_once(watcher_id, correlation_id=None)`.

For each enabled source folder:

1. Validate source path with `PathPolicy`.
2. List files directly under the source root unless requirements explicitly permit recursive behavior.
3. Ignore directories and unsupported temporary/hidden files only if documented.
4. Build a safe display path for logs/events.
5. Create or update file observation state through `FileRepository`.
6. Enqueue `file.detected` for new candidate files.

### Stability

A file is stable when size and mtime are unchanged across the configured stabilization window. Use existing documented environment/settings fields only. Do not add new env vars.

When a file becomes stable:

1. Compute SHA-256.
2. Persist stable metadata.
3. Enqueue `file.stable`.
4. Continue to deduplication/job registration.

### Deduplication

Use a deterministic key such as watcher/source/display path + size + sha256 if the repo docs do not specify a different formula. Persist duplicate observations through `duplicate_suppression_observations` via `FileRepository` or a narrow deduplication repository helper.

If duplicate:

- Do not create a new job.
- Record duplicate suppression observation.
- Log structured duplicate suppression result.

If not duplicate:

- Create job in `REGISTERED` or documented initial job state.
- Append job state history.
- Enqueue `job.registered`.

## Events produced

| Event | Producer | Required source |
|---|---|---|
| `file.detected` | `watcher` | New candidate file observation. |
| `file.stable` | `watcher` | Stable file with SHA-256. |
| `job.registered` | `watcher` | Non-duplicate stable file converted to job. |

Use `app/events/outbox.py` to enqueue. Do not publish directly to Redis.

## Repository use

| Repository | Required WP-06 use |
|---|---|
| `WatcherRepository` | Load watcher configuration, sources, destinations, and lifecycle state. |
| `FileRepository` | Create/get file records, store stability metadata, check duplicate key. |
| `JobRepository` | Create job and append initial job state history. |
| `EventOutboxRepository` | Indirectly via `app/events/outbox.py`; do not call Redis. |
| `StageClaimRepository` | Not required for watcher poll-once unless existing docs require stage claims for watcher. |

## Test checklist

- Route tag normalization rejects invalid route tags through existing schemas or model primitives.
- One source tag maps to multiple matching destinations.
- Multiple source tags map to union of matching destinations.
- Unmatched sources and unmatched destinations are reported.
- Stability detector returns false before window and true after unchanged size/mtime.
- SHA-256 is deterministic and lower-case hex.
- Duplicate key suppresses job registration on second observation.
- `poll_once` enqueues `file.detected`, `file.stable`, and `job.registered` for happy path.
- Invalid or outside-allowlist source path does not leak unsafe host path in logs/errors.

## Out of scope

- Validation/quarantine.
- Processing.
- Delivery.
- Retry scheduling.
- API route creation.
- Streamlit page creation.
- Long-running service runner unless already documented as a WP-06 requirement.

## Verification commands

Run the standard suite plus:

```powershell
pytest tests/watcher
```

Keep evidence current and remove generated/cache artifacts after Sphinx verification.
