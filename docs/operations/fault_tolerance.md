# Fault Tolerance Policy

## Recovery Mechanisms

| Fault | Detection | Required persisted evidence | Recovery mechanism | Verification |
|---|---|---|---|---|
| API restart after command accepted | command row not terminal | `control_commands` row | watcher/retry command worker reconciles command | V-SL-LIFE-001 |
| Watcher restart after job detected | job state `DETECTED` or `STABILIZING` | `jobs`, `job_state_history` | watcher reconciliation resumes stability/register path | V-SL-LIFE-011 |
| Validator restart | jobs in `REGISTERED` or `VALIDATING` | job row, validation attempt if started | validator reconciliation validates or resumes attempt safely | V-SL-LIFE-004 |
| Processor restart | jobs in `VALIDATED` or `PROCESSING` | processing attempt and claim | claim timeout releases eligible job | V-SL-LIFE-006 |
| Delivery restart | jobs in `PROCESSED` or `DELIVERING` | delivery attempts, manifest staging state | delivery reconciliation resumes incomplete destinations | V-SL-LIFE-007 |
| Redis unavailable | outbox pending rows | `event_outbox.status=pending` | outbox dispatcher retries when Redis returns | V-SL-EVT-011 |
| Duplicate event replay | duplicate event ID/idempotency key | `event_offsets`, idempotency records | consumer ignores already processed side effect | V-SL-EVT-003 |
| Destination partial failure | per-destination delivery attempts | `delivery_attempts` | retry only failed destinations; successful finalized outputs remain unchanged | V-SL-OUT-018 |

## Lease and Claim Rules

- Worker stage claims shall include `stage`, `job_id`, `attempt_number`, `worker_id`, `claimed_at`, and `expires_at`.
- Expired claims may be reclaimed by another worker after reconciliation.
- Reclaiming shall not duplicate finalized outputs or terminal state rows.
