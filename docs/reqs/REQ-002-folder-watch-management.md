# REQ-002: Folder Watch Management Requirements

## Capability Intent

The system shall let an operator configure one or more source folders to watch and one or more destination folders to receive processed outputs. Folder configuration is a first-class operational object, not a hardcoded implementation detail. A configured watcher shall be allowed to remain healthy and idle when no files are present, then become active when a stable file arrives and a reachable destination is assigned. Multi-source and multi-destination routing shall be expressible through operator-assigned route tags so the public demo can show many-to-many behavior without a complex rule engine.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-FWM-001 | The system shall allow an operator to create a folder watcher with a unique watcher ID. | Must | V-SL-FWM-001 |
| SL-FWM-002 | A watcher shall include at least one source folder and at least one destination folder. | Must | V-SL-FWM-002 |
| SL-FWM-003 | The system shall support a single-source single-destination watcher. | Must | V-SL-FWM-003 |
| SL-FWM-004 | The system shall support a multi-source single-destination watcher. | Must | V-SL-FWM-004 |
| SL-FWM-005 | The system shall support a single-source multi-destination watcher under the MVP `tag_match_all_destinations` routing policy when one source has at least one normalized tag matching two or more destination folders. | Must | V-SL-FWM-005 |
| SL-FWM-006 | The system shall support multi-source multi-destination configuration under the MVP `tag_match_all_destinations` routing policy when each enabled source and destination has at least one valid normalized route tag. | Must | V-SL-FWM-006 |
| SL-FWM-007 | Each watcher shall have a lifecycle state of `created`, `active`, `paused`, `stopped`, or `error`. | Must | V-SL-FWM-007 |
| SL-FWM-008 | The system shall reject source folders that are not mounted inside the runtime allowlist. | Must | V-SL-FWM-008 |
| SL-FWM-009 | The system shall reject destination folders that are not mounted inside the runtime allowlist. | Must | V-SL-FWM-009 |
| SL-FWM-010 | The system shall persist watcher configuration in PostgreSQL before the watcher becomes active. | Must | V-SL-FWM-010 |
| SL-FWM-011 | The system shall expose watcher create, list, read, update, pause, resume, and stop operations through the API. | Must | V-SL-FWM-011 |
| SL-FWM-012 | The dashboard shall allow operator selection of mounted source and destination roots without requiring code changes. | Must | V-SL-FWM-012 |
| SL-FWM-013 | A started watcher with valid persisted source and destination configuration shall remain in `idle` operational status when no eligible files are present in its source folders. | Must | V-SL-FWM-013 |
| SL-FWM-014 | A watcher in `idle` operational status shall transition to active work within 2 seconds after a stable file is placed in an accessible source folder and at least one reachable destination folder is assigned. | Must | V-SL-FWM-014 |
| SL-FWM-015 | A watcher shall not begin ingestion for a source folder until at least one destination folder is assigned and reachable. | Must | V-SL-FWM-015 |
| SL-FWM-016 | The system shall evaluate source folder access by checking existence, allowlist membership, directory type, and read permission before reporting the source as available. | Must | V-SL-FWM-016 |
| SL-FWM-017 | The system shall evaluate destination folder access by checking existence, allowlist membership, directory type, and write permission before reporting the destination as available. | Must | V-SL-FWM-017 |
| SL-FWM-018 | The system shall persist the latest source and destination reachability status with timestamp, reason code, and operator-safe message. | Must | V-SL-FWM-018 |
| SL-FWM-019 | The system shall expose source and destination reachability status to the API and dashboard without requiring a file to be actively processed. | Must | V-SL-FWM-019 |
| SL-FWM-020 | The system shall allow an operator to assign one or more route tags to each configured source folder. | Must | V-SL-FWM-020 |
| SL-FWM-021 | The system shall allow an operator to assign one or more route tags to each configured destination folder. | Must | V-SL-FWM-021 |
| SL-FWM-022 | Route tags shall be accepted as a semicolon-delimited text value in the dashboard and API, with maximum 20 tags per folder and maximum 32 characters per normalized tag. | Must | V-SL-FWM-022 |
| SL-FWM-023 | The system shall normalize route tags by trimming whitespace, converting tags to uppercase, rejecting empty tags, and deduplicating tags within the same folder configuration. | Must | V-SL-FWM-023 |
| SL-FWM-024 | Route tags shall match regular expression `^[A-Z0-9_-]{1,32}$` after normalization; invalid tags shall reject the watcher create/update request with `422 TAG_INVALID`. | Must | V-SL-FWM-024 |
| SL-FWM-025 | The default MVP routing policy shall be `tag_match_all_destinations`. | Must | V-SL-FWM-025 |
| SL-FWM-026 | Under `tag_match_all_destinations`, an accepted source file shall be routed to every configured destination folder where the source tag set and destination tag set contain at least one matching tag. | Must | V-SL-FWM-026 |
| SL-FWM-027 | The tag matching policy shall support one-to-one, one-to-many, many-to-one, and many-to-many routing without requiring separate rule definitions for each source-destination pair. | Must | V-SL-FWM-027 |
| SL-FWM-028 | A source folder with no matching destination tag shall be marked warning/yellow with reason code `NO_MATCHING_DESTINATION` and shall not create ingestible work until a matching destination is configured. | Must | V-SL-FWM-028 |
| SL-FWM-029 | A destination folder with no matching source tag shall be marked warning/yellow with reason code `NO_MATCHING_SOURCE` while remaining available for future matching sources. | Must | V-SL-FWM-029 |
| SL-FWM-030 | A route shall not be enabled when any source or destination folder has no valid normalized route tags. | Must | V-SL-FWM-030 |
| SL-FWM-031 | The system shall persist normalized tags, original operator-entered tag text, route policy, match preview timestamp, and latest match result for each watcher configuration. | Must | V-SL-FWM-031 |

## Operational Status Model

Folder watchers have a persisted lifecycle state and a derived operational status. Lifecycle state expresses operator intent; operational status expresses what the system is currently able to do.

| Operational status | Meaning | Required source status | Required destination status |
|---|---|---|---|
| `idle` | Watcher is started and healthy but no stable files are available for ingestion. | `green` or `yellow` | `green` |
| `active` | Watcher is processing at least one detected stable file. | `green` | `green` |
| `blocked_source` | Watcher cannot read or transfer from at least one required source folder. | `red` for affected source | `green` or `yellow` |
| `blocked_destination` | Watcher cannot deliver to at least one required destination folder. | `green` or `yellow` | `red` for affected destination |
| `warning` | Watcher is started but at least one non-blocking condition exists: `NO_MATCHING_SOURCE`, `NO_MATCHING_DESTINATION`, `PENDING_CHECK`, or `EMPTY_SOURCE_IDLE`. | `yellow` for affected source | `yellow` for affected destination |

## Source and Destination Health Indicators

| Indicator | Status | Required meaning |
|---|---|---|
| Green | Stable | The source is readable and eligible for transfer, or the destination is reachable and writable. |
| Yellow | Warning | The folder has one of the documented non-blocking reason codes: `PENDING_CHECK`, `EMPTY_SOURCE_IDLE`, `NO_MATCHING_DESTINATION`, `NO_MATCHING_SOURCE`, or `PARTIAL_ROUTE_PREVIEW`; it shall not be used for missing, unreadable, unwritable, or outside-allowlist paths. |
| Red | Faulty | The source cannot be accessed or transferred from, or the destination cannot be reached or written to. |

## Routing Policies

| Policy | Behavior |
|---|---|
| `tag_match_all_destinations` | Default MVP policy. A source file is delivered to every destination sharing at least one normalized route tag with the source folder. |
| `direct` | Future enhancement. Not implemented in MVP unless a later requirement defines exact matching rules, API schema, verification fixtures, and delivery semantics. |
| `fanout` | Future enhancement. Not implemented in MVP unless a later requirement defines exact matching rules, API schema, verification fixtures, and delivery semantics. |
| `rule_based` | Future enhancement. Not implemented in MVP unless a later requirement defines rule language, precedence, error handling, API schema, verification fixtures, and delivery semantics. |

## Tag Matching Behavior

| Scenario | Required result |
|---|---|
| Source tags `A` and destination tags `A` | Source files route to that destination. |
| Source tags `A` and destinations tagged `A`, `A;B`, and `C` | Source files route to the first two destinations only. |
| Sources tagged `A` and `B`, destination tagged `A;B` | Files from both sources route to the destination. |
| Source tags `A;B;C` and destinations tagged `A`, `B`, and `C` | One source file routes to all three matching destinations. |
| Source tag has no destination match | Source routing status is yellow with `NO_MATCHING_DESTINATION`; ingestion for that source is blocked until a match exists. |
| Destination tag has no source match | Destination routing status is yellow with `NO_MATCHING_SOURCE`; destination remains saved and available. |

Route matching expression:

```text
normalized_source_tags intersection normalized_destination_tags is not empty
```

## Route Tag Error Codes

| Code | Trigger | HTTP status | Blocking behavior |
|---|---|---:|---|
| `TAG_EMPTY` | A semicolon segment is empty after trimming. | 422 | Reject create/update. |
| `TAG_INVALID` | A normalized tag fails `^[A-Z0-9_-]{1,32}$`. | 422 | Reject create/update. |
| `TAG_LIMIT_EXCEEDED` | More than 20 unique normalized tags are supplied for one folder. | 422 | Reject create/update. |
| `NO_MATCHING_DESTINATION` | A source has valid tags but zero matched destinations. | 200 preview / 409 start | Saved as warning; watcher start is blocked for that source. |
| `NO_MATCHING_SOURCE` | A destination has valid tags but zero matched sources. | 200 preview | Saved as warning; destination remains available. |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-FWM-NFR-001 | Maximum configured watchers for local demo | >= 10 |
| SL-FWM-NFR-002 | Maximum configured source folders per watcher | >= 5 |
| SL-FWM-NFR-003 | Maximum configured destination folders per watcher | >= 5 |
| SL-FWM-NFR-004 | Watcher create API p95 latency | <= 300 ms |
| SL-FWM-NFR-005 | Watcher state update API p95 latency | <= 300 ms |
| SL-FWM-NFR-006 | Invalid path rejection accuracy | 100% for fixture set |
| SL-FWM-NFR-007 | Idle-to-active transition after stable file arrival | <= 2 seconds |
| SL-FWM-NFR-008 | Source/destination reachability status freshness while dashboard is open | <= dashboard refresh interval + 1 second |
| SL-FWM-NFR-009 | Health indicator correctness for access-denied and missing-folder fixtures | 100% |
| SL-FWM-NFR-010 | Tag normalization correctness for valid and invalid tag fixture set | 100% |
| SL-FWM-NFR-011 | Route preview correctness for one-to-one, one-to-many, many-to-one, and many-to-many tag fixtures | 100% |

## Acceptance Criteria

The requirement is accepted when an operator can create, pause, resume, and stop watchers from the dashboard and API, including at least one single-folder and one multi-folder configuration; a started watcher remains idle when no source files are present; the watcher becomes active after a stable source file arrives with a reachable destination assigned; source and destination health indicators correctly show green, yellow, and red states for fixture conditions; tag-based routing proves one-to-one, one-to-many, many-to-one, and many-to-many delivery matching; and all watcher state transitions, tag normalization results, match previews, and reachability results are persisted and visible after service restart.

## L2 Contract Decomposition Requirements

These rows decompose watcher management into persisted configuration, lifecycle, reachability, route-tag, and preview contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-FWM-035 | L2 | SL-FWM-001, SL-FWM-002, SL-FWM-010, SL-FWM-031 | Watcher configuration contract | A watcher configuration shall persist watcher ID, lifecycle state, route policy, source collection, destination collection, original route tag text, normalized route tag arrays, created/updated timestamps, and latest command correlation ID. | Must | V-SL-FWM-035 |
| SL-FWM-036 | L2 | SL-FWM-007, SL-FWM-011, SL-FWM-013, SL-FWM-014, SL-FWM-015 | Watcher lifecycle command contract | Create, pause, resume, update, and stop commands shall define allowed source state, target state, persistence order, command result, invalid-state response, log event, metric, and dashboard message. | Must | V-SL-FWM-036 |
| SL-FWM-037 | L2 | SL-FWM-016, SL-FWM-017, SL-FWM-018, SL-FWM-019 | Folder reachability contract | Reachability checks shall persist role, locator, health color, reason code, checked timestamp, permission result, and operator-safe message without requiring a file to be present. | Must | V-SL-FWM-037 |
| SL-FWM-038 | L2 | SL-FWM-020, SL-FWM-021, SL-FWM-022, SL-FWM-023, SL-FWM-024 | Route tag normalization contract | Route tag normalization shall preserve original text, produce de-duplicated normalized tags, enforce count and length limits, and return field-specific validation errors for invalid segments. | Must | V-SL-FWM-038 |
| SL-FWM-039 | L2 | SL-FWM-025, SL-FWM-026, SL-FWM-027, SL-FWM-028, SL-FWM-029, SL-FWM-030 | Route preview contract | Route preview shall compute matched destinations per source, unmatched sources, unmatched destinations, aggregate status color, reason codes, and timestamp without creating jobs or reading files. | Must | V-SL-FWM-039 |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-FWM-032 | L3 | SL-FWM-020, SL-FWM-031 | `stream_lite.watchers.repository.save_watcher_config` | The watcher configuration persistence surface shall store watcher core fields, source folders, destination folders, normalized tags, original tag text, route policy, and latest route preview atomically or reject the change without a partial watcher configuration. | V-SL-FWM-032 |
| SL-FWM-033 | L3 | SL-FWM-024, SL-FWM-030 | `stream_lite.watchers.routing.normalize_route_tags` | The route-tag normalization surface shall split semicolon-delimited input, trim whitespace, uppercase values, reject empty tokens, reject tokens outside `^[A-Z0-9_-]{1,32}$`, and return field-specific error metadata for API and dashboard display. | V-SL-FWM-033 |
| SL-FWM-034 | L3 | SL-FWM-026, SL-FWM-027, SL-FWM-028, SL-FWM-029 | `stream_lite.watchers.routing.preview_tag_matches` | The route preview surface shall compute matched destinations, unmatched sources, unmatched destinations, status color, and reason codes without touching the filesystem or creating jobs. | V-SL-FWM-034 |
