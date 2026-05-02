# WORKLOG-20260425: Tag Routing and Dashboard Presentation Requirements

## Summary

Updated the requirements baseline to add tag-based multi-source and multi-destination folder routing plus centralized Streamlit dashboard color and layout configuration. The routing model uses semicolon-delimited route tags on source and destination folders and routes files to every destination sharing at least one normalized tag.

## Files Changed

- `stream_lite/docs/reqs/REQ-002-folder-watch-management.md`
- `stream_lite/docs/reqs/REQ-008-output-delivery.md`
- `stream_lite/docs/reqs/REQ-010-fastapi-control-plane.md`
- `stream_lite/docs/reqs/REQ-011-streamlit-command-center.md`
- `stream_lite/docs/reqs/REQ-012-operational-logging-and-observability.md`
- `stream_lite/docs/reqs/REQ-014-verification-and-acceptance.md`
- `stream_lite/docs/reqs/INDEX.md`
- `stream_lite/docs/reqs/CURRENT_REQUIREMENTS_RECAP.md`
- `stream_lite/docs/master_overview.md`
- `stream_lite/docs/README.md`
- `stream_lite/docs/design/INDEX.md`
- `stream_lite/docs/design/DEC-001-tag-based-folder-routing.md`
- `stream_lite/docs/design/DEC-002-centralized-dashboard-presentation.md`

## Requirements Affected

- SL-FWM-020 through SL-FWM-031
- SL-OUT-016 through SL-OUT-020
- SL-API-016 through SL-API-021
- SL-UI-022 through SL-UI-034
- SL-OBS-015 through SL-OBS-017
- SL-VER-016 through SL-VER-019

## Decisions Applied

- DEC-001: Use `tag_match_all_destinations` as the default MVP routing policy.
- DEC-002: Use centralized dashboard presentation configuration for theme tokens and layout profiles.

## Tests and Verification

No runtime code was executed because this patch is requirements and design documentation only. Verification requirements were added for tag normalization, route preview, many-to-many delivery, partial destination failure, and centralized dashboard presentation configuration.

## Assumptions

- Route tags are operator-provided strings entered as semicolon-delimited text.
- Tags are normalized to uppercase and safe characters before persistence.
- Green/yellow/red remain semantic health states even if dashboard display colors are later customized.
- `tag_match_all_destinations` is MVP scope; `direct`, `fanout`, and `rule_based` remain future or optional unless separately requirements-backed.

## Gaps

- API route specs in `docs/api/` still need to be expanded in a future patch.
- Event schemas for route preview and delivery outcomes still need formal schemas.
- Prometheus metric names need to be added to the future metrics catalog.
- Centralized dashboard configuration file format has not yet been implemented.

## Rollback Notes

Rollback by reverting the files listed above. No code, database migration, or environment variable changes were introduced.

## Next Step

Create API route specifications and JSON schemas for watcher configuration, route tag normalization, route preview, destination delivery outcomes, and dashboard presentation configuration.
