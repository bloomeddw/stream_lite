# WORKLOG-20260505-wp11a-streamlit-foundation-warning-token-fix

## Summary

Closed a WP11-A follow-up gap after the Streamlit foundation tests passed with one unraisable tempfile warning. The patch also corrected the foundation theme helper so documented yellow folder-health reason codes map to the warning semantic token instead of neutral.

## Requirements affected

- `SL-UI-018`: pending/no-match folder health reasons display yellow.
- `SL-UI-019`: inaccessible/unwritable source and destination failures display red.
- `SL-UI-030`: status display uses centralized semantic tokens.
- `SL-UI-034`: green/stable, yellow/warning, and red/faulty semantic mapping is preserved.

## Files changed

- `streamlit_app/theme.py`
- `tests/streamlit_app/test_api_client.py`
- `tests/streamlit_app/test_theme_layout.py`
- `docs/worklogs/WORKLOG-20260505-wp11a-streamlit-foundation-warning-token-fix.md`
- `docs/worklogs/INDEX.md`

## Implementation notes

- Added documented warning reason-code aliases: `PENDING_CHECK`, `EMPTY_SOURCE_IDLE`, `NO_MATCHING_SOURCE`, `NO_MATCHING_DESTINATION`, and `PARTIAL_ROUTE_PREVIEW`.
- Added documented faulty path/transfer/write aliases for red/faulty token resolution.
- Added a `close()` method to the test fake HTTP error body so Python 3.14 does not emit a tempfile deallocator warning after `HTTPError` test coverage.

## Tests run

- `python3 -m py_compile streamlit_app/*.py tests/streamlit_app/*.py`
- `python3 -S tools/contract_lint.py --write-inventory`
- `python3 tools/validate_schema_examples.py --write-evidence`

## Assumptions

- Full Streamlit page rendering remains WP11-B; this patch only adjusts foundation helpers and tests.
- The API remains the source of truth for health and reason-code values; the helper only maps known stable codes to semantic presentation tokens.

## Gaps

- None for WP11-A foundation after this patch and full test verification.

## Rollback notes

Revert the changed theme helper aliases, the two Streamlit foundation tests, this worklog, and the worklog index entry.

## Next step

After full verification passes without warnings, proceed to WP11-B Streamlit app shell and operator pages.
