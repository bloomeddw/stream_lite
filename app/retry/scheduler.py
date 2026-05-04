"""Retry scheduling and due-retry orchestration for WP-10."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app import ensure_uuid_str
from app.events.outbox import LIFECYCLE_STREAM_NAME, enqueue_event
from app.repositories.events import EventOutboxRepository
from app.repositories.jobs import ALLOWED_JOB_TRANSITIONS, JobRepository
from app.repositories.retry import RetryRepository

from .backoff import BackoffPolicy
from .classifier import RetryClassifier

RETRY_SCHEDULER_SERVICE = "retry_scheduler"
REASON_JOB_NOT_FOUND = "JOB_NOT_FOUND"
REASON_INVALID_ATTEMPT_NUMBER = "INVALID_ATTEMPT_NUMBER"
REASON_INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
REASON_RETRY_NOT_DUE = "RETRY_NOT_DUE"
REASON_RETRY_SCHEDULE_NOT_FOUND = "RETRY_SCHEDULE_NOT_FOUND"
REASON_RETRY_SCHEDULE_NOT_SCHEDULED = "RETRY_SCHEDULE_NOT_SCHEDULED"
REASON_RETRY_SCHEDULED = "RETRY_SCHEDULED"
REASON_RETRY_DUE = "RETRY_DUE"
REASON_RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
REASON_NON_RETRYABLE_FAILURE = "NON_RETRYABLE_FAILURE"
SCHEMA_VERSION = "1.0.0"

_RETRY_STAGE_TO_JOB_STATE = {
    "validation": "VALIDATING",
    "processing": "PROCESSING",
    "delivery": "DELIVERING",
}


@dataclass(frozen=True, slots=True)
class RetryScheduleResult:
    job_id: UUID | str | None
    status: Literal["scheduled", "terminal", "exhausted", "skipped"]
    reason_code: str
    final_state: str | None
    attempt_number: int | None
    retry_schedule_id: UUID | None = None
    due_at: datetime | None = None
    event_type: str | None = None
    final_failure_class: str | None = None


@dataclass(frozen=True, slots=True)
class RetryDueResult:
    retry_schedule_id: UUID | str | None
    job_id: UUID | str | None
    status: Literal["attempted", "exhausted", "failed", "skipped"]
    reason_code: str
    final_state: str | None
    attempt_number: int | None
    next_stage: str | None = None
    event_type: str | None = None


@dataclass(frozen=True, slots=True)
class RetryBatchResult:
    scanned: int
    attempted: int
    exhausted: int
    skipped: int
    failed: int


class RetryScheduler:
    """Persist retry schedules, finalize terminal failures, and release due retries."""

    def __init__(
        self,
        *,
        session: Session | None = None,
        retry_repository: RetryRepository | None = None,
        job_repository: JobRepository | None = None,
        event_repository: EventOutboxRepository | None = None,
        classifier: RetryClassifier | None = None,
        backoff_policy: BackoffPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if backoff_policy is None:
            raise ValueError("backoff_policy is required")
        if session is None and any(
            dependency is None
            for dependency in (retry_repository, job_repository, event_repository)
        ):
            raise ValueError("session or all repository instances are required")

        inferred_session = session or next(
            repository.session
            for repository in (retry_repository, job_repository, event_repository)
            if repository is not None
        )

        self.session = inferred_session
        self.retry_repository = retry_repository or RetryRepository(inferred_session)
        self.job_repository = job_repository or JobRepository(inferred_session)
        self.event_repository = event_repository or EventOutboxRepository(inferred_session)
        self.classifier = classifier or RetryClassifier()
        self.backoff_policy = backoff_policy
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def schedule_retry_for_job(
        self,
        job_id: UUID | str,
        failed_stage: str,
        error_code: str,
        correlation_id: str | None = None,
    ) -> RetryScheduleResult:
        job = self.job_repository.get_job(job_id)
        if job is None:
            return RetryScheduleResult(
                job_id=str(job_id),
                status="skipped",
                reason_code=REASON_JOB_NOT_FOUND,
                final_state=None,
                attempt_number=None,
            )

        resolved_correlation_id = ensure_uuid_str(correlation_id or job.correlation_id, field_name="correlation_id")
        classification = self.classifier.classify(stage=failed_stage, error_code=error_code)
        current_attempt_number = _resolve_attempt_number(job.attempt_number)
        if current_attempt_number is None:
            return RetryScheduleResult(
                job_id=job.job_id,
                status="skipped",
                reason_code=REASON_INVALID_ATTEMPT_NUMBER,
                final_state=job.state,
                attempt_number=job.attempt_number,
            )

        transitioned_at = self.clock()
        previous_state = job.state

        if not classification.retryable:
            terminal_state = classification.terminal_state_when_not_retryable
            if terminal_state is None or not _transition_allowed(previous_state, terminal_state):
                return RetryScheduleResult(
                    job_id=job.job_id,
                    status="skipped",
                    reason_code=REASON_INVALID_STATE_TRANSITION,
                    final_state=previous_state,
                    attempt_number=current_attempt_number,
                )

            self.job_repository.update_state(
                job.job_id,
                new_state=terminal_state,
                latest_error_code=classification.error_code,
                attempt_number=current_attempt_number,
            )
            self.job_repository.append_state_history(
                job_id=job.job_id,
                previous_state=previous_state,
                new_state=terminal_state,
                actor_service=RETRY_SCHEDULER_SERVICE,
                reason_code=REASON_NON_RETRYABLE_FAILURE,
                correlation_id=resolved_correlation_id,
                transitioned_at=transitioned_at,
            )

            event_type = None
            final_failure_class = None
            if terminal_state == "FAILED" and _supports_job_failed_stage(classification.stage):
                self._enqueue_job_failed(
                    job=job,
                    correlation_id=resolved_correlation_id,
                    occurred_at=transitioned_at,
                    failed_stage=classification.stage,
                    attempt_number=current_attempt_number,
                    final_failure_class="non_retryable",
                    last_error_code=classification.error_code,
                    operator_message=classification.operator_message,
                )
                event_type = "job.failed"
                final_failure_class = "non_retryable"

            return RetryScheduleResult(
                job_id=job.job_id,
                status="terminal",
                reason_code=REASON_NON_RETRYABLE_FAILURE,
                final_state=terminal_state,
                attempt_number=current_attempt_number,
                event_type=event_type,
                final_failure_class=final_failure_class,
            )

        if classification.stage not in _RETRY_STAGE_TO_JOB_STATE:
            return RetryScheduleResult(
                job_id=job.job_id,
                status="skipped",
                reason_code=REASON_INVALID_STATE_TRANSITION,
                final_state=previous_state,
                attempt_number=current_attempt_number,
            )

        if not _transition_allowed(previous_state, "RETRY_PENDING"):
            return RetryScheduleResult(
                job_id=job.job_id,
                status="skipped",
                reason_code=REASON_INVALID_STATE_TRANSITION,
                final_state=previous_state,
                attempt_number=current_attempt_number,
            )

        if not self.backoff_policy.retry_allowed_after_attempt(current_attempt_number):
            self.job_repository.update_state(
                job.job_id,
                new_state="FAILED",
                latest_error_code=classification.error_code,
                attempt_number=current_attempt_number,
            )
            self.job_repository.append_state_history(
                job_id=job.job_id,
                previous_state=previous_state,
                new_state="FAILED",
                actor_service=RETRY_SCHEDULER_SERVICE,
                reason_code=REASON_RETRY_EXHAUSTED,
                correlation_id=resolved_correlation_id,
                transitioned_at=transitioned_at,
            )
            self._enqueue_job_failed(
                job=job,
                correlation_id=resolved_correlation_id,
                occurred_at=transitioned_at,
                failed_stage=classification.stage,
                attempt_number=current_attempt_number,
                final_failure_class="exhausted_retries",
                last_error_code=classification.error_code,
                operator_message=_exhausted_operator_message(classification.stage),
            )
            return RetryScheduleResult(
                job_id=job.job_id,
                status="exhausted",
                reason_code=REASON_RETRY_EXHAUSTED,
                final_state="FAILED",
                attempt_number=current_attempt_number,
                event_type="job.failed",
                final_failure_class="exhausted_retries",
            )

        next_attempt_number = self.backoff_policy.next_attempt_number(current_attempt_number)
        if next_attempt_number is None:
            return RetryScheduleResult(
                job_id=job.job_id,
                status="exhausted",
                reason_code=REASON_RETRY_EXHAUSTED,
                final_state=previous_state,
                attempt_number=current_attempt_number,
            )

        backoff_seconds = float(self.backoff_policy.next_delay_seconds(current_attempt_number))
        due_at = _as_utc(transitioned_at) + timedelta(seconds=backoff_seconds)
        schedule = self.retry_repository.schedule_retry(
            job_id=job.job_id,
            failed_stage=classification.stage,
            failure_class=classification.failure_class,
            due_at=due_at,
            backoff_seconds=backoff_seconds,
            attempt_number=next_attempt_number,
            max_attempts=self.backoff_policy.max_attempts,
            jitter_enabled=self.backoff_policy.jitter_enabled,
            next_stage=classification.stage,
            last_error_code=classification.error_code,
            correlation_id=resolved_correlation_id,
        )
        self.job_repository.update_state(
            job.job_id,
            new_state="RETRY_PENDING",
            latest_error_code=classification.error_code,
            attempt_number=next_attempt_number,
        )
        self.job_repository.append_state_history(
            job_id=job.job_id,
            previous_state=previous_state,
            new_state="RETRY_PENDING",
            actor_service=RETRY_SCHEDULER_SERVICE,
            reason_code=REASON_RETRY_SCHEDULED,
            correlation_id=resolved_correlation_id,
            transitioned_at=transitioned_at,
        )
        self._enqueue_retry_scheduled(
            job=job,
            correlation_id=resolved_correlation_id,
            occurred_at=transitioned_at,
            failed_stage=classification.stage,
            attempt_number=next_attempt_number,
            due_at=due_at,
            backoff_seconds=backoff_seconds,
            retry_reason=classification.operator_message,
        )
        return RetryScheduleResult(
            job_id=job.job_id,
            status="scheduled",
            reason_code=REASON_RETRY_SCHEDULED,
            final_state="RETRY_PENDING",
            attempt_number=next_attempt_number,
            retry_schedule_id=schedule.retry_schedule_id,
            due_at=due_at,
            event_type="retry.scheduled",
        )

    def process_due_retry(
        self,
        retry_schedule_id: UUID | str,
        correlation_id: str | None = None,
    ) -> RetryDueResult:
        schedule = self.retry_repository.get_retry_schedule(retry_schedule_id)
        if schedule is None:
            return RetryDueResult(
                retry_schedule_id=str(retry_schedule_id),
                job_id=None,
                status="skipped",
                reason_code=REASON_RETRY_SCHEDULE_NOT_FOUND,
                final_state=None,
                attempt_number=None,
            )

        if schedule.status != "scheduled":
            return RetryDueResult(
                retry_schedule_id=schedule.retry_schedule_id,
                job_id=schedule.job_id,
                status="skipped",
                reason_code=REASON_RETRY_SCHEDULE_NOT_SCHEDULED,
                final_state=None,
                attempt_number=schedule.attempt_number,
                next_stage=schedule.next_stage,
            )

        now = self.clock()
        if _as_utc(schedule.due_at) > _as_utc(now):
            return RetryDueResult(
                retry_schedule_id=schedule.retry_schedule_id,
                job_id=schedule.job_id,
                status="skipped",
                reason_code=REASON_RETRY_NOT_DUE,
                final_state=None,
                attempt_number=schedule.attempt_number,
                next_stage=schedule.next_stage,
            )

        resolved_correlation_id = ensure_uuid_str(correlation_id or schedule.correlation_id, field_name="correlation_id")
        job = self.job_repository.get_job(schedule.job_id)
        if job is None:
            self.retry_repository.mark_retry_failed(
                schedule.retry_schedule_id,
                last_error_code=REASON_JOB_NOT_FOUND,
            )
            return RetryDueResult(
                retry_schedule_id=schedule.retry_schedule_id,
                job_id=schedule.job_id,
                status="failed",
                reason_code=REASON_JOB_NOT_FOUND,
                final_state=None,
                attempt_number=schedule.attempt_number,
                next_stage=schedule.next_stage,
            )

        if schedule.attempt_number > schedule.max_attempts:
            previous_state = job.state
            if not _transition_allowed(previous_state, "FAILED"):
                self.retry_repository.mark_retry_failed(
                    schedule.retry_schedule_id,
                    last_error_code=schedule.last_error_code or REASON_RETRY_EXHAUSTED,
                )
                return RetryDueResult(
                    retry_schedule_id=schedule.retry_schedule_id,
                    job_id=job.job_id,
                    status="failed",
                    reason_code=REASON_INVALID_STATE_TRANSITION,
                    final_state=previous_state,
                    attempt_number=schedule.attempt_number,
                    next_stage=schedule.next_stage,
                )

            self.retry_repository.mark_retry_exhausted(
                schedule.retry_schedule_id,
                last_error_code=schedule.last_error_code,
            )
            self.job_repository.update_state(
                job.job_id,
                new_state="FAILED",
                latest_error_code=schedule.last_error_code,
                attempt_number=schedule.attempt_number,
            )
            self.job_repository.append_state_history(
                job_id=job.job_id,
                previous_state=previous_state,
                new_state="FAILED",
                actor_service=RETRY_SCHEDULER_SERVICE,
                reason_code=REASON_RETRY_EXHAUSTED,
                correlation_id=resolved_correlation_id,
                transitioned_at=now,
            )
            self._enqueue_job_failed(
                job=job,
                correlation_id=resolved_correlation_id,
                occurred_at=now,
                failed_stage=schedule.failed_stage,
                attempt_number=schedule.attempt_number,
                final_failure_class="exhausted_retries",
                last_error_code=schedule.last_error_code or REASON_RETRY_EXHAUSTED,
                operator_message=_exhausted_operator_message(schedule.failed_stage),
            )
            return RetryDueResult(
                retry_schedule_id=schedule.retry_schedule_id,
                job_id=job.job_id,
                status="exhausted",
                reason_code=REASON_RETRY_EXHAUSTED,
                final_state="FAILED",
                attempt_number=schedule.attempt_number,
                next_stage=schedule.next_stage,
                event_type="job.failed",
            )

        target_state = _retry_target_state(schedule.next_stage)
        previous_state = job.state
        if target_state is None or previous_state != "RETRY_PENDING" or not _transition_allowed(previous_state, target_state):
            self.retry_repository.mark_retry_failed(
                schedule.retry_schedule_id,
                last_error_code=schedule.last_error_code or REASON_INVALID_STATE_TRANSITION,
            )
            return RetryDueResult(
                retry_schedule_id=schedule.retry_schedule_id,
                job_id=job.job_id,
                status="failed",
                reason_code=REASON_INVALID_STATE_TRANSITION,
                final_state=previous_state,
                attempt_number=schedule.attempt_number,
                next_stage=schedule.next_stage,
            )

        self.job_repository.update_state(
            job.job_id,
            new_state=target_state,
            attempt_number=schedule.attempt_number,
        )
        self.job_repository.append_state_history(
            job_id=job.job_id,
            previous_state=previous_state,
            new_state=target_state,
            actor_service=RETRY_SCHEDULER_SERVICE,
            reason_code=REASON_RETRY_DUE,
            correlation_id=resolved_correlation_id,
            transitioned_at=now,
        )
        self.retry_repository.mark_retry_attempted(schedule.retry_schedule_id)
        return RetryDueResult(
            retry_schedule_id=schedule.retry_schedule_id,
            job_id=job.job_id,
            status="attempted",
            reason_code=REASON_RETRY_DUE,
            final_state=target_state,
            attempt_number=schedule.attempt_number,
            next_stage=schedule.next_stage,
        )

    def process_due_retries(
        self,
        limit: int = 100,
        correlation_id: str | None = None,
    ) -> RetryBatchResult:
        due_schedules = self.retry_repository.claim_due_retries(
            as_of=self.clock(),
            limit=max(limit, 0),
        )
        attempted = 0
        exhausted = 0
        skipped = 0
        failed = 0

        for schedule in due_schedules:
            result = self.process_due_retry(schedule.retry_schedule_id, correlation_id=correlation_id)
            if result.status == "attempted":
                attempted += 1
            elif result.status == "exhausted":
                exhausted += 1
            elif result.status == "failed":
                failed += 1
            else:
                skipped += 1

        return RetryBatchResult(
            scanned=len(due_schedules),
            attempted=attempted,
            exhausted=exhausted,
            skipped=skipped,
            failed=failed,
        )

    def _enqueue_retry_scheduled(
        self,
        *,
        job,
        correlation_id: str,
        occurred_at: datetime,
        failed_stage: str,
        attempt_number: int,
        due_at: datetime,
        backoff_seconds: float,
        retry_reason: str,
    ) -> None:
        enqueue_event(
            self.event_repository,
            stream_name=LIFECYCLE_STREAM_NAME,
            idempotency_key=_retry_scheduled_idempotency_key(job.job_id, failed_stage, attempt_number),
            event_payload={
                "schema_version": SCHEMA_VERSION,
                "correlation_id": correlation_id,
                "job_id": job.job_id,
                "watcher_id": job.watcher_id,
                "attempt_number": attempt_number,
                "occurred_at": _format_rfc3339(occurred_at),
                "producer": RETRY_SCHEDULER_SERVICE,
                "event_type": "retry.scheduled",
                "payload": {
                    "next_stage": failed_stage,
                    "due_at": _format_rfc3339(due_at),
                    "backoff_seconds": backoff_seconds,
                    "max_attempts": self.backoff_policy.max_attempts,
                    "retry_reason": retry_reason,
                },
            },
        )

    def _enqueue_job_failed(
        self,
        *,
        job,
        correlation_id: str,
        occurred_at: datetime,
        failed_stage: str,
        attempt_number: int,
        final_failure_class: str,
        last_error_code: str,
        operator_message: str,
    ) -> None:
        if not _supports_job_failed_stage(failed_stage):
            return

        enqueue_event(
            self.event_repository,
            stream_name=LIFECYCLE_STREAM_NAME,
            idempotency_key=_job_failed_idempotency_key(job.job_id, failed_stage, attempt_number),
            event_payload={
                "schema_version": SCHEMA_VERSION,
                "correlation_id": correlation_id,
                "job_id": job.job_id,
                "watcher_id": job.watcher_id,
                "attempt_number": attempt_number,
                "occurred_at": _format_rfc3339(occurred_at),
                "producer": RETRY_SCHEDULER_SERVICE,
                "event_type": "job.failed",
                "payload": {
                    "final_failure_class": final_failure_class,
                    "exhausted_stage": failed_stage,
                    "last_error_code": last_error_code,
                    "operator_message": operator_message,
                },
            },
        )


def _resolve_attempt_number(value: int | None) -> int | None:
    if value is None or value < 1:
        return None
    return int(value)


def _retry_target_state(retry_stage: str) -> str | None:
    return _RETRY_STAGE_TO_JOB_STATE.get(retry_stage)


def _supports_job_failed_stage(stage: str) -> bool:
    return stage in {"validation", "processing", "delivery", "routing"}


def _transition_allowed(previous_state: str, new_state: str) -> bool:
    if previous_state == new_state:
        return True
    return new_state in ALLOWED_JOB_TRANSITIONS.get(previous_state, set())


def _retry_scheduled_idempotency_key(job_id: UUID | str, failed_stage: str, attempt_number: int) -> str:
    return f"retry.scheduled:{job_id}:{failed_stage}:{attempt_number}"


def _job_failed_idempotency_key(job_id: UUID | str, failed_stage: str, attempt_number: int) -> str:
    return f"job.failed:{job_id}:{failed_stage}:{attempt_number}"


def _exhausted_operator_message(failed_stage: str) -> str:
    return f"Retry attempts are exhausted for the {failed_stage} stage and the job has failed."


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_rfc3339(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


__all__ = [
    "RetryBatchResult",
    "RetryDueResult",
    "RetryScheduleResult",
    "RetryScheduler",
]
