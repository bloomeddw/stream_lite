# Stream Lite Documentation

This folder contains requirements documentation for a Dockerized, event-driven file ingestion platform intended for a public, readable, testable architecture demo.

## Contents

- `master_overview.md` — product demo overview, intent, architecture, workflow, success criteria, and traceability model.
- `reqs/INDEX.md` — active requirement index and cleanup notes for removed duplicate drafts.
- `reqs/CURRENT_REQUIREMENTS_RECAP.md` — recap of what is currently captured and the recommended next requirement pass.
- `reqs/REQ-*.md` — capability-level requirements documents.
- `worklogs/` — documentation and patch worklogs.

## Requirements Structure

The active requirement baseline uses one capability document per `REQ-###` number. Individual requirements inside those files use the stable `SL-<CAPABILITY>-<NUMBER>` convention. Verification cases use `V-SL-<CAPABILITY>-<NUMBER>`.

Each requirement document should capture, where applicable:

1. Capability intent.
2. In-scope and out-of-scope behavior.
3. Functional requirements using SHALL language.
4. Data, schema, interface, environment, route, logging, metric, and operational requirements.
5. Nonfunctional targets with measurable thresholds.
6. Acceptance criteria and verification methods.
7. Evidence artifacts required to close the requirement.

## Verification Philosophy

A requirement is not closed because code exists. A requirement is closed when there is evidence that the behavior works under defined conditions. Evidence should be stored under:

```text
stream_lite/docs/verification/<verification_id>/
```

Recommended evidence files:

- `case_manifest.json`
- `inputs/`
- `actual/`
- `expected/`
- `comparison.json`
- `summary.md`

## Cleanup Note

The previous documentation set accidentally mixed two requirement versions. The duplicate draft files were removed from the active baseline, and their unique content was migrated into the correct active requirement files. See `reqs/INDEX.md` and `reqs/CURRENT_REQUIREMENTS_RECAP.md` for details.

## Current Requirements Additions

- Tag-based multi-source/multi-destination routing using semicolon-delimited source and destination route tags.
- Route preview requirements showing which destinations match each source before a watcher is enabled.
- Per-destination delivery outcome requirements for partial multi-destination failures.
- Centralized Streamlit theme and layout configuration requirements.
