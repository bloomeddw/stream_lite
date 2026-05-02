# WORKLOG-20260501-wp06-watcher-implementation

## Summary

Implemented the WP-06 watcher-side orchestration slice for route-tag matching, direct source-folder polling, file stability detection, SHA-256 calculation, duplicate suppression, job registration, and lifecycle outbox enqueueing.

## Files changed

- `app/watcher/__init__.py`
- `app/watcher/routing.py`
- `app/watcher/stability.py`
- `app/watcher/deduplication.py`
- `app/watcher/service.py`
- `tests/watcher/test_routing.py`
- `tests/watcher/test_stability.py`
- `tests/watcher/test_deduplication.py`
- `tests/watcher/test_service.py`
- `docs/worklogs/INDEX.md`
- `docs/worklogs/WORKLOG-20260501-wp06-watcher-implementation.md`

## Requirements affected

- `SL-FWM-006`, `SL-FWM-020` through `SL-FWM-030`, `SL-FWM-033`
- `SL-FDI-001` through `SL-FDI-029`
- `SL-EVT-001`, `SL-EVT-002`, `SL-EVT-003`
- `SL-JOB-035`, `SL-JOB-036`
- `SL-LIFE-001` through `SL-LIFE-006`
- `SL-OBS-003`, `SL-OBS-006`, `SL-OBS-015`
- `SL-SEC-001` through `SL-SEC-017` where source paths and logs are handled

## Decisions applied

- `DEC-001-tag-based-folder-routing`: route matching uses `tag_match_all_destinations` and normalized route-tag intersections.
- `DEC-009-uuid-generation-ownership`: watcher service generates UUIDs before persistence side effects.
- `DEC-010-event-stream-naming`: watcher events are enqueued to `stream_lite.lifecycle` through the outbox.

## Tests and verification

Static syntax verification completed in the review sandbox:

```bash
python -S -m py_compile app/watcher/routing.py app/watcher/stability.py app/watcher/deduplication.py app/watcher/service.py app/watcher/__init__.py tests/watcher/test_routing.py tests/watcher/test_stability.py tests/watcher/test_deduplication.py tests/watcher/test_service.py
```

Full pytest, schema example validation, and Sphinx verification still need to be run in the project virtual environment after applying the patch.

## Assumptions

- WP-06 remains a poll-once orchestration slice and does not introduce a long-running daemon.
- Source scanning is direct-child only and ignores directories.
- Pre-stable file observations are maintained in `WatcherService` memory for MVP polling because no durable pre-stable observation table exists in the current WP-03 schema.
- `file.detected`, `file.stable`, and `job.registered` are enqueued together once a stable unique file can be assigned a file record, deduplication key, and job ID.

## Gaps

- No new migrations were added.
- Durable pre-stable observations remain a future enhancement unless a later requirement introduces a storage surface.
- Watcher-specific Prometheus counters are not added because the current metrics helper surface is not sufficient for a new metrics framework in WP-06 scope.

## Rollback notes

Remove the `app/watcher/` package, `tests/watcher/` package, and this worklog/index entry to return to the WP-06 readiness-only state.

## Next step

Run the full WP-06 verification suite. If all commands pass, WP-06 can be marked ready for WP-07 validation/quarantine work.
