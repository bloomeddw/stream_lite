# DEC-001: Tag-Based Folder Routing

## Status

Accepted for MVP requirements.

## Context

Stream Lite needs a public-demo-friendly way to show multi-source and multi-destination routing without requiring operators to author a complex rule engine. The operator proposed assigning one or more semicolon-delimited IDs or letters to each source and destination folder, then routing source files to every destination sharing an ID.

## Decision

The MVP routing policy shall be named `tag_match_all_destinations`.

Each source folder and destination folder can be assigned semicolon-delimited route tags. The system shall normalize tags by trimming whitespace, converting to uppercase, rejecting empty tags, deduplicating tags within a folder configuration, and allowing only uppercase letters, numbers, underscores, and hyphens after normalization.

A source file shall route to every destination folder where the normalized source tag set and normalized destination tag set share at least one tag.

## Options Considered

| Option | Pros | Cons |
|---|---|---|
| Explicit source-to-destination mapping table | Very precise; easy to audit exact pairs. | More manual entry; grows quickly for many-to-many setups; less demo-friendly. |
| Rule-based routing by filename or metadata | Powerful and extensible. | Requires rule grammar, validation, conflict handling, and more verification. |
| Tag-based routing | Simple to explain; supports one-to-one, one-to-many, many-to-one, and many-to-many; easy to preview in Streamlit. | Less expressive than a full rules engine; needs clear normalization and warning behavior. |

## Consequences

- Requirements now define route tags on source and destination folders.
- API contracts now include tag validation and route preview behavior.
- Streamlit must show tag inputs, normalized tags, and route preview before enablement.
- Output delivery must record per-destination outcomes and matched route tags.
- Verification must cover one-to-one, one-to-many, many-to-one, many-to-many, unmatched source, and unmatched destination scenarios.

## Related Requirements

- SL-FWM-020 through SL-FWM-031
- SL-OUT-016 through SL-OUT-020
- SL-API-016 through SL-API-020
- SL-UI-022 through SL-UI-029
- SL-VER-016 through SL-VER-018
