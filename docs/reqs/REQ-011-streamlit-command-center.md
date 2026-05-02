# REQ-011: Streamlit Command Center Requirements

## Capability Intent

The Streamlit dashboard shall serve as the operator command center. It shall let users configure watchers, browse and enter mounted folders, assign route tags to source and destination folders, preview multi-source and multi-destination matches, start and stop ingestion, monitor active or idle work, inspect failures, view source/destination health, and trigger manual retries without directly accessing the database or event broker. Dashboard colors and layout shall be centrally configurable so demo styling can change without rewriting each page.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-UI-001 | The dashboard shall display API and dependency health status. | Must | V-SL-UI-001 |
| SL-UI-002 | The dashboard shall allow the operator to create a watcher with one or more source folders. | Must | V-SL-UI-002 |
| SL-UI-003 | The dashboard shall allow the operator to select one or more destination folders. | Must | V-SL-UI-003 |
| SL-UI-004 | The dashboard shall expose `tag_match_all_destinations` as the only enabled MVP routing policy and shall display `direct`, `fanout`, and `rule_based` as disabled future options unless later requirements activate them. | Must | V-SL-UI-004 |
| SL-UI-005 | The dashboard shall allow start, pause, resume, and stop actions for watchers. | Must | V-SL-UI-005 |
| SL-UI-006 | The dashboard shall show job counts by state. | Must | V-SL-UI-006 |
| SL-UI-007 | The dashboard shall show a recent jobs table with state, file name, watcher, timestamps, attempts, and terminal status. | Must | V-SL-UI-007 |
| SL-UI-008 | The dashboard shall provide filters for watcher, state, and time range. | Should | V-SL-UI-008 |
| SL-UI-009 | The dashboard shall show job detail, state history, validation results, processing attempts, delivery attempts, and error codes. | Must | V-SL-UI-009 |
| SL-UI-010 | The dashboard shall provide a manual retry action for eligible failed jobs. | Should | V-SL-UI-010 |
| SL-UI-011 | The dashboard shall refresh operational views using `refresh_interval_seconds` from `DashboardPresentationResponse`, default `2`, allowed integer range `1` through `60`. | Must | V-SL-UI-011 |
| SL-UI-012 | The dashboard shall call the FastAPI API and shall not directly write PostgreSQL records. | Must | V-SL-UI-012 |
| SL-UI-013 | The dashboard shall provide a filepath text box for each source folder and destination folder field. | Must | V-SL-UI-013 |
| SL-UI-014 | The dashboard shall provide a browse-folders control next to each source and destination filepath box that lists API-approved mounted folders. | Must | V-SL-UI-014 |
| SL-UI-015 | The dashboard shall allow an operator to add source folders and destination folders to a watcher from the dashboard without editing configuration files or restarting services. | Must | V-SL-UI-015 |
| SL-UI-016 | The dashboard shall display a colored status dot next to each source folder and destination folder. | Must | V-SL-UI-016 |
| SL-UI-017 | The dashboard shall display green status when a source is readable and transferable or a destination is reachable and writable. | Must | V-SL-UI-017 |
| SL-UI-018 | The dashboard shall display yellow status when a source or destination is pending validation, has reason code `PENDING_CHECK`, `NO_MATCHING_SOURCE`, or `NO_MATCHING_DESTINATION`, or has a non-blocking warning code defined by the folder health contract. | Must | V-SL-UI-018 |
| SL-UI-019 | The dashboard shall display red status when a source cannot be accessed or transferred from, or a destination cannot be reached or written to. | Must | V-SL-UI-019 |
| SL-UI-020 | The dashboard shall show idle status for a started watcher that has valid source and destination folders but no eligible files to process. | Must | V-SL-UI-020 |
| SL-UI-021 | The dashboard shall show active status within 2 seconds after an idle watcher detects a stable file and begins work. | Must | V-SL-UI-021 |
| SL-UI-022 | The dashboard shall provide a route tags text input for each source folder and each destination folder. | Must | V-SL-UI-022 |
| SL-UI-023 | The route tags text input shall accept semicolon-delimited values and show the normalized tag list returned by the API. | Must | V-SL-UI-023 |
| SL-UI-024 | The dashboard shall provide a route preview control that shows matched destination folders for each configured source folder before the watcher is enabled. | Must | V-SL-UI-024 |
| SL-UI-025 | The dashboard shall show unmatched source folders as yellow with reason `NO_MATCHING_DESTINATION`. | Must | V-SL-UI-025 |
| SL-UI-026 | The dashboard shall show unmatched destination folders as yellow with reason `NO_MATCHING_SOURCE`. | Must | V-SL-UI-026 |
| SL-UI-027 | The dashboard shall support the `tag_match_all_destinations` route policy as the default MVP routing behavior. | Must | V-SL-UI-027 |
| SL-UI-028 | The dashboard shall show a per-source routing preview that lists destination path, destination status, and matched route tags. | Must | V-SL-UI-028 |
| SL-UI-029 | The dashboard shall block watcher enablement when API route validation reports invalid tags, red folder health, or missing valid tags. | Must | V-SL-UI-029 |
| SL-UI-030 | The dashboard shall load color values from a centralized dashboard presentation configuration rather than hardcoding status colors in individual page sections. | Must | V-SL-UI-030 |
| SL-UI-031 | The dashboard shall load layout section ordering, visibility, and grouping from a centralized dashboard layout configuration rather than hardcoding layout decisions in individual page sections. | Must | V-SL-UI-031 |
| SL-UI-032 | The dashboard shall support at least two centralized layout profiles, `operator_default` and `reviewer_demo`, loaded from the dashboard presentation configuration endpoint or local fallback config. | Must | V-SL-UI-032 |
| SL-UI-033 | The dashboard shall support at least two centralized color themes, `default_light` and `high_contrast`, loaded from the dashboard presentation configuration endpoint or local fallback config. | Must | V-SL-UI-033 |
| SL-UI-034 | Color scheme configuration shall preserve the semantic mapping of green/stable, yellow/warning, and red/faulty even when display color tokens are changed. | Must | V-SL-UI-034 |

## Folder Setup Controls

| Control | API mapping | Related requirements | Required behavior |
|---|---|---|---|
| Source filepath box | `POST /files/validate-path` and watcher mutation endpoints | SL-UI-013, SL-API-014, SL-FWM-016 | Accepts a path, validates it as a source candidate, and blocks save on red status. |
| Source browse button | `GET /files/browse?purpose=source` | SL-UI-014, SL-API-013 | Shows only mounted allowlisted source candidates returned by the API. |
| Destination filepath box | `POST /files/validate-path` and watcher mutation endpoints | SL-UI-013, SL-API-014, SL-FWM-017 | Accepts a path, validates it as a destination candidate, and blocks start on red status. |
| Destination browse button | `GET /files/browse?purpose=destination` | SL-UI-014, SL-API-013 | Shows only mounted allowlisted destination candidates returned by the API. |
| Add source/destination | `PATCH /watchers/{watcher_id}` | SL-UI-015, SL-FWM-002 | Adds the folder to persisted watcher configuration after successful validation. |
| Source route tags box | `PATCH /watchers/{watcher_id}` and `POST /watchers/{watcher_id}/preview-routes` | SL-UI-022, SL-FWM-020, SL-FWM-022 | Accepts semicolon-delimited source tags and displays normalized tags or validation errors. |
| Destination route tags box | `PATCH /watchers/{watcher_id}` and `POST /watchers/{watcher_id}/preview-routes` | SL-UI-022, SL-FWM-021, SL-FWM-022 | Accepts semicolon-delimited destination tags and displays normalized tags or validation errors. |
| Preview routes button | `POST /watchers/{watcher_id}/preview-routes` | SL-UI-024, SL-API-018, SL-FWM-026 | Shows source-to-destination matches and unmatched folder warnings before enablement. |
| Dashboard theme selector | `GET /config/dashboard-presentation` | SL-UI-030, SL-UI-033, SL-API-021 | Loads available theme tokens and applies the selected theme without changing routing behavior. |
| Dashboard layout selector | `GET /config/dashboard-presentation` | SL-UI-031, SL-UI-032, SL-API-021 | Loads available layout profiles and applies section ordering and visibility from centralized configuration. |

## Route Tag UI Semantics

| UI element | Required behavior |
|---|---|
| Source tag input | Accepts operator text such as `A;B;CLIENT-001`; submits to API for normalization and validation. |
| Destination tag input | Accepts operator text such as `A;B;ARCHIVE`; submits to API for normalization and validation. |
| Normalized tag display | Shows the API-normalized tag list so the operator can see what will be persisted. |
| Match preview | Shows every destination that will receive files from each source and the matched tag or tags that caused the match. |
| Unmatched warning | Uses yellow status and stable reason codes instead of treating incomplete matching as a filesystem fault. |

## Dashboard Presentation Configuration

| Configuration area | Requirement |
|---|---|
| Color scheme | Shall be defined through centralized semantic tokens for stable, warning, faulty, neutral, accent, background, text, and disabled states. |
| Status dots | Shall use semantic health states from the API and display colors from the active theme. |
| Layout | Shall be defined through centralized section ordering, grouping, page visibility, and card/table density values. |
| Change scope | Shall allow color and layout changes without editing individual watcher, job, health, and log display sections. |
| Safety | Shall not allow a theme to change the underlying health meaning of green/stable, yellow/warning, or red/faulty. |

## Health Dot Semantics

| Dot color | Label | Source meaning | Destination meaning |
|---|---|---|---|
| Green | Stable | Source folder can be accessed and files can be transferred from it. | Destination folder is reachable and writable. |
| Yellow | Warning | Source folder is valid but has reason code `PENDING_CHECK`, `EMPTY_SOURCE_IDLE`, or `NO_MATCHING_DESTINATION`. | Destination folder is valid but has reason code `PENDING_CHECK`, `NO_MATCHING_SOURCE`, or `PARTIAL_ROUTE_PREVIEW`. |
| Red | Faulty | Source folder cannot be accessed or transfer from it failed. | Destination folder cannot be reached, written, or finalized. |

## Dashboard Views

- System health.
- Watcher setup.
- Watcher control.
- Source and destination folder health.
- Route tag preview.
- Jobs overview.
- Job detail.
- Failure and quarantine queue.
- Operational logs.
- Demo metrics summary.

## Streamlit Control Contract

| Control | API endpoint | Success behavior | Failure behavior | Log/metric |
|---|---|---|---|---|
| Create watcher | `POST /watchers` | Shows watcher detail and route preview prompt. | Shows API error code and field-level message. | `stream_lite_dashboard_action_total{action="create_watcher"}` |
| Validate folder | `POST /files/validate-path` | Shows green/yellow/red dot and reason message. | Shows `PATH_VALIDATION_FAILED` message without host-only paths. | `stream_lite_dashboard_action_total{action="validate_folder"}` |
| Browse folder | `GET /files/browse` | Shows only allowlisted candidate folders. | Shows retryable API error and preserves current form values. | `stream_lite_dashboard_action_total{action="browse_folder"}` |
| Preview routes | `POST /watchers/{watcher_id}/preview-routes` | Shows matched destinations and unmatched warnings. | Shows tag or path errors and blocks start button. | `stream_lite_dashboard_action_total{action="preview_routes"}` |
| Start watcher | `POST /watchers/{watcher_id}/start` | Transitions lifecycle display to started/active or idle. | Shows `409` state conflict or validation error. | `stream_lite_dashboard_action_total{action="start_watcher"}` |
| Retry job | `POST /jobs/{job_id}/retry` | Shows accepted command and later retry attempt after command status succeeds. | Shows `JOB_NOT_RETRYABLE` or current state. | `stream_lite_dashboard_action_total{action="retry_job"}` |
| View command status | `GET /commands/{command_id}` | Shows command state, target resource, result locator, and latest message. | Shows `COMMAND_STATUS_UNAVAILABLE` and keeps previous command card visible. | `stream_lite_dashboard_action_total{action="view_command_status"}` |

## Usability Requirements for Demo Review

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-UI-035 | Primary demo tasks shall be available from the first dashboard page without requiring direct database, broker, or filesystem shell access. | Must | V-SL-UI-035 |
| SL-UI-036 | Every operator action that changes system state shall provide visible success or failure feedback within one dashboard refresh interval after the API response. | Must | V-SL-UI-036 |
| SL-UI-037 | Form fields for folder paths and route tags shall include examples and validation hints before submission. | Must | V-SL-UI-037 |
| SL-UI-038 | When an API mutation returns `202`, the dashboard shall display the command as accepted and poll `GET /commands/{command_id}` until the command reaches `succeeded`, `failed`, or `expired`. | Must | V-SL-UI-038 |

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-UI-NFR-001 | Default refresh interval | 2 seconds |
| SL-UI-NFR-002 | Dashboard page interaction p95 after API response | <= 500 ms |
| SL-UI-NFR-003 | Supported visible jobs in table before pagination/filtering required | >= 1,000 |
| SL-UI-NFR-004 | Dashboard uses API for mutations | 100% of mutation actions |
| SL-UI-NFR-005 | User-visible error message for failed API call | 100% of handled API failures |
| SL-UI-NFR-006 | Folder status dot update latency after API reports changed health | <= one dashboard refresh interval |
| SL-UI-NFR-007 | Browse control returns disallowed folders to the UI | 0 disallowed folders |
| SL-UI-NFR-008 | Idle-to-active dashboard status update after stable file detection | <= 2 seconds plus one dashboard refresh interval |
| SL-UI-NFR-009 | Route preview correctness displayed for tag matching fixture set | 100% |
| SL-UI-NFR-010 | Centralized theme token usage for health dots, cards, buttons, and warning banners | 100% of Streamlit display components in MVP scope |
| SL-UI-NFR-011 | Centralized layout profile usage for dashboard section ordering and visibility | 100% of dashboard pages in MVP scope |

## Acceptance Criteria

The requirement is accepted when an operator can run the entire demo from the dashboard: create watcher, browse or type source and destination folders, enter semicolon-delimited route tags, validate folder health, preview tag-based source-to-destination matches, start watching, observe idle status with no files present, drop files, observe active work, monitor jobs, see green/yellow/red source and destination dots for fixture scenarios, switch dashboard color and layout profiles through centralized presentation configuration, inspect errors, and retry eligible failures.

## Dashboard Configuration Storage Contract

| Area | Requirement |
|---|---|
| Source of defaults | v0.1 dashboard presentation defaults shall live in a versioned YAML file at `stream_lite/config/dashboard_presentation.yaml`. |
| API exposure | The API shall expose the resolved YAML configuration through `GET /config/dashboard-presentation`. |
| Mutation scope | v0.1 shall not persist presentation changes through API mutation endpoints; theme and layout selection in the dashboard is session-local unless a later requirement adds saved preferences. |
| Startup fallback | If the API is unavailable during dashboard startup, the dashboard may load the local YAML fallback read-only and shall display yellow status `PRESENTATION_API_UNAVAILABLE`. |
| Schema validation | Invalid YAML shape, unknown theme name, unknown layout profile, or missing required status tokens shall block dashboard startup with `PRESENTATION_CONFIG_INVALID`. |

## Applied Decision Records

| Decision | Requirement impact |
|---|---|
| DEC-007 dashboard configuration storage | v0.1 uses versioned YAML defaults exposed through a read-only presentation configuration API. |

## L2 Contract Decomposition Requirements

These rows decompose the Streamlit command center into API-backed view, mutation control, async feedback, presentation, and error-display contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-UI-042 | L2 | SL-UI-001, SL-UI-002, SL-UI-005 | Dashboard data-source contract | The dashboard shall read health, watchers, jobs, events, validation failures, quarantine, retries, outputs, logs, and metric summaries from documented APIs, not direct database/broker access. | Must | V-SL-UI-042 |
| SL-UI-043 | L2 | SL-UI-003, SL-UI-006, SL-UI-007, SL-UI-008 | Dashboard mutation control contract | Every dashboard mutation control shall map to one API route, request schema, allowed UI states, validation rule, success/failure response, log event, metric, and requirement ID. | Must | V-SL-UI-043 |
| SL-UI-044 | L2 | SL-UI-031, SL-UI-036, SL-UI-038 | Async command feedback contract | For `202` mutations, the dashboard shall display command ID, command status, latest operator-safe message, retryable flag when applicable, and terminal result after polling. | Must | V-SL-UI-044 |
| SL-UI-045 | L2 | SL-UI-004, SL-UI-035 | Presentation configuration contract | Theme and layout shall load from centralized presentation config, expose active theme/layout in the UI, and use documented fallback when API config is unavailable. | Must | V-SL-UI-045 |
| SL-UI-046 | L2 | SL-UI-009, SL-UI-010, SL-UI-011 | Dashboard error and empty-state contract | API failures, empty tables, invalid inputs, and unavailable dependencies shall produce operator-safe messages with correlation ID when available and no secrets or host-only paths. | Must | V-SL-UI-046 |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-UI-039 | L3 | SL-UI-001, SL-UI-035 | `stream_lite.dashboard.pages.operator_command_center.render` | The command center page surface shall render health, watchers, jobs, events, validation failures, quarantine, retries, outputs, logs, and metric summaries without requiring shell access. | V-SL-UI-039 |
| SL-UI-040 | L3 | SL-UI-004, SL-UI-031, SL-UI-033 | `stream_lite.dashboard.presentation.load_presentation_config` | The presentation configuration surface shall load theme and layout from the API response when available, fall back to local config when unavailable, and display a warning when fallback is active. | V-SL-UI-040 |
| SL-UI-041 | L3 | SL-UI-036, SL-UI-038 | `stream_lite.dashboard.commands.submit_and_track_command` | The command submission surface shall submit API mutations, display accepted command IDs for `202` responses, and poll command status until terminal state. | V-SL-UI-041 |
