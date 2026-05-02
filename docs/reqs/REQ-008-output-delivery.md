# REQ-008: Output Delivery Requirements

## Capability Intent

The system shall deliver processed outputs to configured destination folders according to watcher routing policy, preserve delivery metadata, avoid duplicate or partial output delivery, and make source or destination transfer faults visible to the operator.

## Functional Requirements

| ID | Requirement | Priority | Verification |
|---|---|---:|---|
| SL-OUT-001 | The delivery service shall consume jobs in `PROCESSED` state. | Must | V-SL-OUT-001 |
| SL-OUT-002 | The delivery service shall transition jobs to `DELIVERING` before writing to destination folders. | Must | V-SL-OUT-002 |
| SL-OUT-003 | The delivery service shall resolve destination folders using the watcher's routing policy. | Must | V-SL-OUT-003 |
| SL-OUT-004 | The delivery service shall write outputs to a temporary destination locator before finalizing delivery. | Must | V-SL-OUT-004 |
| SL-OUT-005 | The delivery service shall finalize local filesystem delivery with atomic rename within the same mounted filesystem; if same-filesystem atomic rename is unavailable, delivery shall fail with `FINALIZE_UNSUPPORTED` and shall not expose a finalized output path. | Must | V-SL-OUT-005 |
| SL-OUT-006 | The delivery service shall record one delivery attempt per destination. | Must | V-SL-OUT-006 |
| SL-OUT-007 | A job shall transition to `DELIVERED` only after all required destination deliveries succeed. | Must | V-SL-OUT-007 |
| SL-OUT-008 | A job shall transition from `DELIVERED` to `COMPLETED`. | Must | V-SL-OUT-008 |
| SL-OUT-009 | Delivery failures shall be retryable unless caused by permanent path policy violation. | Must | V-SL-OUT-009 |
| SL-OUT-010 | The system shall publish `delivery.completed` for each successful destination delivery. | Must | V-SL-OUT-010 |
| SL-OUT-011 | The system shall publish `job.completed` after final job completion. | Must | V-SL-OUT-011 |
| SL-OUT-012 | Delivered output filenames or parent path segments shall include `job_id=<job_id>` exactly once so an operator can trace a delivered artifact to one job without database access. | Must | V-SL-OUT-012 |
| SL-OUT-013 | Before each delivery attempt, the delivery service shall verify that the selected destination folder is reachable, allowlisted, and writable. | Must | V-SL-OUT-013 |
| SL-OUT-014 | If a delivery attempt cannot reach or write to the selected destination, the system shall mark the affected destination health indicator as `red`, record a delivery failure reason code, and apply retry policy when the failure is retryable. | Must | V-SL-OUT-014 |
| SL-OUT-015 | If source access fails before or during transfer, the system shall mark the affected source health indicator as `red`, record a source transfer failure reason code, and prevent the job from being reported as delivered. | Must | V-SL-OUT-015 |
| SL-OUT-016 | For `tag_match_all_destinations`, the delivery service shall create one required destination delivery attempt for every destination that shares at least one normalized route tag with the source folder. | Must | V-SL-OUT-016 |
| SL-OUT-017 | The delivery service shall record the matched route tag or tags that caused each destination delivery attempt. | Must | V-SL-OUT-017 |
| SL-OUT-018 | If one matched destination succeeds and another matched destination fails, the system shall preserve per-destination delivery outcomes instead of collapsing the job into a single generic failure reason. | Must | V-SL-OUT-018 |
| SL-OUT-019 | A job with at least one successful matched destination and at least one failed or exhausted matched destination shall transition to terminal state `COMPLETED_WITH_DELIVERY_ERRORS` rather than `COMPLETED`. | Must | V-SL-OUT-019 |
| SL-OUT-020 | A source file with zero matched destinations shall not enter delivery and shall record reason code `NO_MATCHING_DESTINATION`. | Must | V-SL-OUT-020 |

## Tag-Based Delivery Contract

| Field | Requirement |
|---|---|
| `source_folder_id` | Shall identify the configured source folder that produced the job. |
| `destination_folder_id` | Shall identify the matched destination folder for an individual delivery attempt. |
| `source_route_tags` | Shall contain normalized source tags used for route resolution. |
| `destination_route_tags` | Shall contain normalized destination tags used for route resolution. |
| `matched_route_tags` | Shall contain the non-empty tag intersection that caused the destination match. |
| `delivery_outcome` | Shall be tracked independently per destination as `pending`, `succeeded`, `retry_pending`, `failed`, or `skipped`. |

## Output Layout

Default local demo output:

```text
<destination_root>/
  watcher_id=<watcher_id>/
    date=YYYY-MM-DD/
      job_id=<job_id>/
        output.<extension>
        processing_summary.json
        delivery_manifest.json
```

## Delivery Failure Reason Codes

| Code | Retryable | Trigger |
|---|---:|---|
| `DESTINATION_NOT_FOUND` | yes | Destination path was allowlisted but missing at attempt time. |
| `DESTINATION_NOT_WRITABLE` | yes | Destination path exists but write check or write operation failed. |
| `DESTINATION_NOT_ALLOWLISTED` | no | Destination path fails allowlist check. |
| `FINALIZE_UNSUPPORTED` | no | Atomic same-filesystem finalize cannot be performed. |
| `FINALIZE_FAILED` | yes | Atomic rename failed after staging write. |
| `SOURCE_TRANSFER_FAILED` | yes | Source or staged processed artifact could not be read during delivery. |
| `NO_MATCHING_DESTINATION` | no | Route resolution returned zero destinations. |

## Partial Delivery Contract

For multi-destination delivery, each destination attempt shall have an independent terminal outcome. Successful destinations shall keep finalized outputs; failed destinations shall keep only temporary artifacts until cleanup. The job terminal state shall summarize the aggregate outcome, but operator-facing APIs shall expose every destination outcome.

## Nonfunctional Requirements and Metrics

| ID | Metric Requirement | Target |
|---|---|---:|
| SL-OUT-NFR-001 | Delivery latency p95 for outputs <= 10 MB | <= 2 seconds |
| SL-OUT-NFR-002 | Delivery manifest creation | 100% of completed jobs |
| SL-OUT-NFR-003 | Partial final output visibility under simulated failure | 0 finalized partial outputs |
| SL-OUT-NFR-004 | Duplicate delivery under duplicate event replay | 0 duplicate finalized outputs |
| SL-OUT-NFR-005 | Fanout delivery completeness | 100% configured destinations or job not completed |
| SL-OUT-NFR-006 | Destination health red-state detection after unreachable destination fixture | <= 2 seconds after failed write attempt |
| SL-OUT-NFR-007 | Source health red-state detection after source access failure fixture | <= 2 seconds after failed read/transfer attempt |
| SL-OUT-NFR-008 | Destination delivery attempt completeness for tag matches | 100% of matched destinations receive an attempt or recorded skip reason |
| SL-OUT-NFR-009 | Per-destination partial failure explainability | 100% of partial delivery fixtures include destination-level outcome and reason code |

## Acceptance Criteria

The requirement is accepted when outputs are delivered to the correct folder structure, delivery attempts are recorded per matched destination, matched route tags are captured in delivery metadata, partial outputs do not appear as finalized files after simulated failures, duplicate delivery events do not create duplicate final outputs, partial multi-destination failures preserve destination-level outcomes, and source or destination transfer failures produce the correct red health indicator and operator-safe reason code.

## L2 Contract Decomposition Requirements

These rows decompose output delivery into target resolution, atomic delivery, per-destination attempts, partial delivery, manifests, and failure/final-state contracts.

| ID | Level | Parent requirement IDs | Contract surface | Requirement | Priority | Verification |
|---|---|---|---|---|---:|---|
| SL-OUT-024 | L2 | SL-OUT-001, SL-OUT-002, SL-OUT-003, SL-FWM-026 | Delivery target resolution contract | Delivery target resolution shall use normalized route tags or persisted preview, create one destination attempt per matched destination, and refuse delivery when no destination is matched or reachable. | Must | V-SL-OUT-024 |
| SL-OUT-025 | L2 | SL-OUT-004, SL-OUT-005, SL-OUT-006, SL-OUT-010 | Atomic filesystem delivery contract | Delivery shall write to a temporary locator under the destination root, verify bytes/checksum, then finalize by rename or documented equivalent before recording finalized locator. | Must | V-SL-OUT-025 |
| SL-OUT-026 | L2 | SL-OUT-007, SL-OUT-008, SL-OUT-009, SL-OUT-020 | Per-destination attempt contract | Each destination attempt shall record destination ID, matched tags, attempt number, start/end timestamps, temporary locator, finalized locator, manifest locator, status, checksum, and failure code. | Must | V-SL-OUT-026 |
| SL-OUT-027 | L2 | SL-OUT-011, SL-OUT-012, SL-OUT-013 | Partial delivery contract | A failed destination shall not roll back finalized successful destinations; mixed success/failure shall use `COMPLETED_WITH_DELIVERY_ERRORS` when retry is unavailable or exhausted. | Must | V-SL-OUT-027 |
| SL-OUT-028 | L2 | SL-OUT-014, SL-OUT-015, SL-OUT-016 | Delivery manifest contract | Delivery shall create/update a manifest listing job ID, source identity, output checksum, destination attempts, finalized locators, failed destinations, and operator-safe failure messages. | Must | V-SL-OUT-028 |
| SL-OUT-029 | L2 | SL-OUT-017, SL-OUT-018, SL-OUT-019, SL-OUT-023 | Delivery failure and final-state contract | Delivery failure handling shall classify reason, persist attempts, schedule retry when eligible, emit events/logs, and compute final state after all matched destinations are terminal or retry-pending. | Must | V-SL-OUT-029 |

## L3 Implementation Surface Traceability

| ID | Level | Parent | Surface | Requirement | Verification |
|---|---|---|---|---|---|
| SL-OUT-021 | L3 | SL-OUT-016, SL-OUT-017 | `stream_lite.delivery.routing.resolve_delivery_targets` | The delivery target surface shall create one required destination attempt for each matched destination and persist matched tags for each attempt. | V-SL-OUT-021 |
| SL-OUT-022 | L3 | SL-OUT-013, SL-OUT-014 | `stream_lite.delivery.filesystem.copy_output_to_destination` | The filesystem delivery surface shall verify destination reachability and writability before copying, preserve per-destination failure reason codes, and avoid marking a destination delivered until copy and manifest update succeed. | V-SL-OUT-022 |
| SL-OUT-023 | L3 | SL-OUT-018, SL-OUT-019 | `stream_lite.delivery.service.finalize_delivery_state` | The delivery finalization surface shall compute terminal job state from per-destination outcomes and use `COMPLETED_WITH_DELIVERY_ERRORS` when at least one matched destination failed or exhausted retries. | V-SL-OUT-023 |
