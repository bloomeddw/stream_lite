"""Manual retry acceptance and retry handoff primitives for WP-10C."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Literal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app import ensure_uuid_str, generate_uuid, generate_uuid_str
from app.db.models import DeliveryAttemptModel, ProcessingAttemptModel, RetryScheduleModel
from app.events.outbox import LIFECYCLE_STREAM_NAME, enqueue_event
from app.repositories.commands import CommandRepository
from app.repositories.events import EventOutboxRepository
from app.repositories.jobs import JobRepository
from app.repositories.retry import RetryRepository

from .backoff import BackoffPolicy
from .classifier import RetryClassifier
from .scheduler import RetryScheduler

MANUAL_RETRY_REASON_CODE = "MANUAL_RETRY_REQUESTED"
RETRY_SCHEDULER_SERVICE = "retry_scheduler"
SCHEMA_VERSION = "1.0.0"
COMMAND_TYPE = "job.retry"
COMMAND_RESOURCE_TYPE = "job"
RETRY_SCHEDULE_FAILED = "RETRY_SCHEDULE_FAILED"
UNKNOWN_FAILURE = "UNKNOWN_FAILURE"
_FAILED_STAGES = frozenset({"processing", "delivery"})


@dataclass(frozen=True, slots=True)
class ManualRetryResult:
    command_id: UUID
    job_id: UUID
    accepted_at: str
    correlation_id: str
    command_status: Literal["accepted", "running", "succeeded", "failed", "expired"]
    retry_schedule_id: UUID | None
    failed_stage: Literal["processing", "delivery"] | None
    attempt_number: int | None
    manual_override: bool | None
    error_code: str | None = None
    idempotency_reused: bool = False


@dataclass(frozen=True, slots=True)
class _FailedStageContext:
    stage: Literal["processing", "delivery"]
    attempt_number: int | None
    error_code: str | None
    failed_at: datetime


class ManualRetryError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        error_code: str,
        message: str,
        correlation_id: str,
        field: str | None = None,
        resource_id: str | None = None,
        current_state: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.correlation_id = correlation_id
        self.field = field
        self.resource_id = resource_id
        self.current_state = current_state


class ManualRetryService:
    """Accept manual retry commands and hand work back to the retry scheduler flow."""

    def __init__(
        self,
        *,
        session: Session | None = None,
        command_repository: CommandRepository | None = None,
        job_repository: JobRepository | None = None,
        retry_repository: RetryRepository | None = None,
        event_repository: EventOutboxRepository | None = None,
        retry_scheduler: RetryScheduler | None = None,
        classifier: RetryClassifier | None = None,
        backoff_policy: BackoffPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        inferred_session = session or next(
            (
                repository.session
                for repository in (
                    command_repository,
                    job_repository,
                    retry_repository,
                    event_repository,
                )
                if repository is not None
            ),
            getattr(retry_scheduler, "session", None),
        )
        if inferred_session is None:
            raise ValueError("session or repository instances are required")

        self.session = inferred_session
        self.command_repository = command_repository or CommandRepository(inferred_session)
        self.job_repository = job_repository or JobRepository(inferred_session)
        self.retry_repository = retry_repository or RetryRepository(inferred_session)
        self.event_repository = event_repository or EventOutboxRepository(inferred_session)
        self.classifier = classifier or getattr(retry_scheduler, "classifier", None) or RetryClassifier()
        self.backoff_policy = backoff_policy or getattr(retry_scheduler, "backoff_policy", None)
        if self.backoff_policy is None:
            raise ValueError("backoff_policy is required")
        self.clock = clock or getattr(retry_scheduler, "clock", None) or (lambda: datetime.now(timezone.utc))
        self.retry_scheduler = retry_scheduler or RetryScheduler(
            session=inferred_session,
            retry_repository=self.retry_repository,
            job_repository=self.job_repository,
            event_repository=self.event_repository,
            classifier=self.classifier,
            backoff_policy=self.backoff_policy,
            clock=self.clock,
        )

    def accept_manual_retry_command(
        self,
        job_id: UUID | str,
        requested_by: str,
        operator_reason: str | None,
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
    ) -> ManualRetryResult:
        resolved_correlation_id = ensure_uuid_str(correlation_id, field_name="correlation_id")
        resolved_reason = (operator_reason or "").strip()
        if not resolved_reason:
            raise ManualRetryError(
                status_code=422,
                error_code="REQUEST_VALIDATION_FAILED",
                message="reason is required for manual retry commands.",
                field="reason",
                correlation_id=resolved_correlation_id,
            )

        scope = _idempotency_scope(job_id)
        payload_hash = _payload_hash(
            {
                "requested_by": requested_by,
                "reason": operator_reason,
            },
        )
        if idempotency_key is not None:
            existing_record = self.command_repository.get_key(scope=scope, idempotency_key=idempotency_key)
            if existing_record is not None:
                if existing_record.payload_hash is not None and existing_record.payload_hash != payload_hash:
                    raise ManualRetryError(
                        status_code=409,
                        error_code="IDEMPOTENCY_KEY_CONFLICT",
                        message="Idempotency-Key was already used with a different request payload.",
                        correlation_id=resolved_correlation_id,
                        resource_id=str(job_id),
                    )
                if existing_record.first_response_json is not None:
                    return self._result_from_existing_response(existing_record.first_response_json)

        job = self.job_repository.get_job(job_id)
        if job is None:
            raise ManualRetryError(
                status_code=404,
                error_code="JOB_NOT_FOUND",
                message=f"Job {job_id} was not found.",
                correlation_id=resolved_correlation_id,
                resource_id=str(job_id),
            )

        resolved_correlation_id = ensure_uuid_str(correlation_id or job.correlation_id, field_name="correlation_id")
        if job.state != "FAILED":
            raise ManualRetryError(
                status_code=409,
                error_code="JOB_NOT_RETRYABLE",
                message="Only FAILED jobs are retryable.",
                correlation_id=resolved_correlation_id,
                resource_id=str(job.job_id),
                current_state=job.state,
            )

        failed_context = self._infer_failed_stage(job.job_id)
        if failed_context is None:
            raise ManualRetryError(
                status_code=409,
                error_code="JOB_NOT_RETRYABLE",
                message="The latest failed stage is not retryable.",
                correlation_id=resolved_correlation_id,
                resource_id=str(job.job_id),
                current_state=job.state,
            )

        error_code = failed_context.error_code or job.latest_error_code or UNKNOWN_FAILURE
        classification = self.classifier.classify(
            stage=failed_context.stage,
            error_code=error_code,
        )
        manual_override = not classification.retryable
        if classification.terminal_state_when_not_retryable == "QUARANTINED":
            raise ManualRetryError(
                status_code=409,
                error_code="JOB_NOT_RETRYABLE",
                message="Validation-policy failures are not manually retryable.",
                correlation_id=resolved_correlation_id,
                resource_id=str(job.job_id),
                current_state=job.state,
            )

        current_attempt_number = _resolve_current_attempt_number(job.attempt_number, failed_context.attempt_number)
        if current_attempt_number is None:
            raise ManualRetryError(
                status_code=409,
                error_code="JOB_NOT_RETRYABLE",
                message="The latest failed stage does not have a retryable attempt number.",
                correlation_id=resolved_correlation_id,
                resource_id=str(job.job_id),
                current_state=job.state,
            )
        if not self.backoff_policy.retry_allowed_after_attempt(current_attempt_number):
            raise ManualRetryError(
                status_code=409,
                error_code="RETRY_LIMIT_EXHAUSTED",
                message="Retry attempts are exhausted for this job.",
                correlation_id=resolved_correlation_id,
                resource_id=str(job.job_id),
                current_state=job.state,
            )

        next_attempt_number = self.backoff_policy.next_attempt_number(current_attempt_number)
        if next_attempt_number is None:
            raise ManualRetryError(
                status_code=409,
                error_code="RETRY_LIMIT_EXHAUSTED",
                message="Retry attempts are exhausted for this job.",
                correlation_id=resolved_correlation_id,
                resource_id=str(job.job_id),
                current_state=job.state,
            )

        created = self.command_repository.create_command(
            command_id=generate_uuid(),
            command_type=COMMAND_TYPE,
            target_resource_type=COMMAND_RESOURCE_TYPE,
            target_resource_id=job.job_id,
            requested_by=requested_by,
            operator_reason=resolved_reason,
            idempotency_key=idempotency_key or generate_uuid_str(),
            correlation_id=resolved_correlation_id,
        )
        accepted_at = _format_rfc3339(created.created_at)
        accepted_response_json = _accepted_response_json(
            command_id=created.command_id,
            job_id=job.job_id,
            accepted_at=accepted_at,
            correlation_id=resolved_correlation_id,
        )
        if idempotency_key is not None:
            self.command_repository.reserve_idempotency_key(
                idempotency_key_id=generate_uuid(),
                scope=scope,
                idempotency_key=idempotency_key,
                target_type=COMMAND_RESOURCE_TYPE,
                target_id=job.job_id,
                payload_hash=payload_hash,
                first_response_json=accepted_response_json,
            )

        try:
            now = _as_utc(self.clock())
            schedule = self.retry_repository.schedule_retry(
                job_id=job.job_id,
                failed_stage=failed_context.stage,
                failure_class=classification.failure_class,
                due_at=now,
                backoff_seconds=0.0,
                attempt_number=next_attempt_number,
                max_attempts=self.backoff_policy.max_attempts,
                jitter_enabled=False,
                next_stage=failed_context.stage,
                last_error_code=failed_context.error_code,
                correlation_id=resolved_correlation_id,
            )
            self.job_repository.update_state(
                job.job_id,
                new_state="RETRY_PENDING",
                latest_error_code=failed_context.error_code,
                attempt_number=next_attempt_number,
            )
            self.job_repository.append_state_history(
                job_id=job.job_id,
                previous_state="FAILED",
                new_state="RETRY_PENDING",
                actor_service=RETRY_SCHEDULER_SERVICE,
                reason_code=MANUAL_RETRY_REASON_CODE,
                correlation_id=resolved_correlation_id,
                transitioned_at=now,
            )
            enqueue_event(
                self.event_repository,
                stream_name=LIFECYCLE_STREAM_NAME,
                idempotency_key=_manual_retry_event_idempotency_key(
                    job.job_id,
                    failed_context.stage,
                    next_attempt_number,
                ),
                event_payload={
                    "schema_version": SCHEMA_VERSION,
                    "correlation_id": resolved_correlation_id,
                    "job_id": job.job_id,
                    "watcher_id": job.watcher_id,
                    "attempt_number": next_attempt_number,
                    "occurred_at": _format_rfc3339(now),
                    "producer": RETRY_SCHEDULER_SERVICE,
                    "event_type": "retry.scheduled",
                    "payload": {
                        "next_stage": failed_context.stage,
                        "due_at": _format_rfc3339(now),
                        "backoff_seconds": 0.0,
                        "max_attempts": self.backoff_policy.max_attempts,
                        "retry_reason": _event_retry_reason(resolved_reason),
                    },
                },
            )
            self.command_repository.update_command_status(
                created.command_id,
                status="succeeded",
                result_locator=_command_result_locator(schedule.retry_schedule_id, manual_override=manual_override),
            )
            return ManualRetryResult(
                command_id=created.command_id,
                job_id=job.job_id,
                accepted_at=accepted_at,
                correlation_id=resolved_correlation_id,
                command_status="succeeded",
                retry_schedule_id=schedule.retry_schedule_id,
                failed_stage=failed_context.stage,
                attempt_number=next_attempt_number,
                manual_override=manual_override,
            )
        except Exception as exc:
            error_code = _command_failure_code(exc)
            self.command_repository.update_command_status(
                created.command_id,
                status="failed",
                error_code=error_code,
            )
            return ManualRetryResult(
                command_id=created.command_id,
                job_id=job.job_id,
                accepted_at=accepted_at,
                correlation_id=resolved_correlation_id,
                command_status="failed",
                retry_schedule_id=None,
                failed_stage=failed_context.stage,
                attempt_number=next_attempt_number,
                manual_override=manual_override,
                error_code=error_code,
            )

    def _result_from_existing_response(self, response_json: dict[str, object]) -> ManualRetryResult:
        command_id = UUID(str(response_json["command_id"]))
        job_id = UUID(str(response_json["target_resource_id"]))
        command = self.command_repository.get_command(command_id)
        locator = command.result_locator if command is not None else None
        retry_schedule_id = _parse_retry_schedule_id_from_locator(locator)
        schedule = self.retry_repository.get_retry_schedule(retry_schedule_id) if retry_schedule_id is not None else None
        if schedule is None:
            schedule = self._latest_retry_schedule(job_id)

        failed_stage = None if schedule is None else schedule.failed_stage
        if failed_stage not in _FAILED_STAGES:
            failed_stage = None

        return ManualRetryResult(
            command_id=command_id,
            job_id=job_id,
            accepted_at=str(response_json["accepted_at"]),
            correlation_id=str(response_json["correlation_id"]),
            command_status="accepted" if command is None else command.status,
            retry_schedule_id=None if schedule is None else schedule.retry_schedule_id,
            failed_stage=failed_stage,  # type: ignore[arg-type]
            attempt_number=None if schedule is None else schedule.attempt_number,
            manual_override=_parse_manual_override_from_locator(locator),
            error_code=None if command is None else command.error_code,
            idempotency_reused=True,
        )

    def _latest_retry_schedule(self, job_id: UUID | str) -> RetryScheduleModel | None:
        statement = (
            sa.select(RetryScheduleModel)
            .where(RetryScheduleModel.job_id == UUID(str(job_id)))
            .order_by(RetryScheduleModel.created_at.desc(), RetryScheduleModel.retry_schedule_id.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def _infer_failed_stage(self, job_id: UUID | str) -> _FailedStageContext | None:
        normalized_job_id = UUID(str(job_id))
        latest_delivery_failure = self.session.scalar(
            sa.select(DeliveryAttemptModel)
            .where(
                DeliveryAttemptModel.job_id == normalized_job_id,
                DeliveryAttemptModel.status == "failed",
            )
            .order_by(DeliveryAttemptModel.completed_at.desc().nullslast(), DeliveryAttemptModel.created_at.desc())
            .limit(1)
        )
        latest_processing_failure = self.session.scalar(
            sa.select(ProcessingAttemptModel)
            .where(
                ProcessingAttemptModel.job_id == normalized_job_id,
                ProcessingAttemptModel.status == "failed",
            )
            .order_by(ProcessingAttemptModel.completed_at.desc().nullslast(), ProcessingAttemptModel.created_at.desc())
            .limit(1)
        )

        delivery_context = None if latest_delivery_failure is None else _FailedStageContext(
            stage="delivery",
            attempt_number=latest_delivery_failure.attempt_number,
            error_code=latest_delivery_failure.failure_code,
            failed_at=_failed_at(latest_delivery_failure.completed_at, latest_delivery_failure.created_at),
        )
        processing_context = None if latest_processing_failure is None else _FailedStageContext(
            stage="processing",
            attempt_number=latest_processing_failure.attempt_number,
            error_code=latest_processing_failure.error_code,
            failed_at=_failed_at(latest_processing_failure.completed_at, latest_processing_failure.created_at),
        )

        if delivery_context is not None and processing_context is not None:
            if delivery_context.failed_at >= processing_context.failed_at:
                return delivery_context
            return processing_context
        if delivery_context is not None:
            return delivery_context
        if processing_context is not None:
            return processing_context

        latest_retry_schedule = self.session.scalar(
            sa.select(RetryScheduleModel)
            .where(RetryScheduleModel.job_id == normalized_job_id)
            .where(RetryScheduleModel.failed_stage.in_(tuple(_FAILED_STAGES)))
            .order_by(RetryScheduleModel.created_at.desc(), RetryScheduleModel.retry_schedule_id.desc())
            .limit(1)
        )
        if latest_retry_schedule is None or latest_retry_schedule.failed_stage not in _FAILED_STAGES:
            return None
        return _FailedStageContext(
            stage=latest_retry_schedule.failed_stage,  # type: ignore[arg-type]
            attempt_number=latest_retry_schedule.attempt_number,
            error_code=latest_retry_schedule.last_error_code,
            failed_at=_as_utc(latest_retry_schedule.created_at),
        )


def _accepted_response_json(
    *,
    command_id: UUID,
    job_id: UUID,
    accepted_at: str,
    correlation_id: str,
) -> dict[str, object]:
    return {
        "command_id": str(command_id),
        "status": "accepted",
        "target_resource_type": COMMAND_RESOURCE_TYPE,
        "target_resource_id": str(job_id),
        "accepted_at": accepted_at,
        "correlation_id": correlation_id,
    }


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _command_failure_code(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        message = str(exc)
        if "job not found" in message:
            return "JOB_NOT_FOUND"
        if "invalid state transition" in message:
            return "JOB_NOT_RETRYABLE"
    return RETRY_SCHEDULE_FAILED


def _command_result_locator(retry_schedule_id: UUID, *, manual_override: bool) -> str:
    locator = f"retry_schedule:{retry_schedule_id}"
    if manual_override:
        return f"{locator}?manual_override=true"
    return locator


def _event_retry_reason(operator_reason: str) -> str:
    return operator_reason[:256]


def _failed_at(completed_at: datetime | None, created_at: datetime) -> datetime:
    return _as_utc(completed_at or created_at)


def _format_rfc3339(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _idempotency_scope(job_id: UUID | str) -> str:
    return f"{COMMAND_TYPE}:{job_id}"


def _manual_retry_event_idempotency_key(job_id: UUID | str, failed_stage: str, attempt_number: int) -> str:
    return f"retry.scheduled:{job_id}:manual:{failed_stage}:{attempt_number}"


def _parse_manual_override_from_locator(locator: str | None) -> bool | None:
    if not locator:
        return None
    return "manual_override=true" in locator


def _parse_retry_schedule_id_from_locator(locator: str | None) -> UUID | None:
    if not locator or not locator.startswith("retry_schedule:"):
        return None
    value = locator.removeprefix("retry_schedule:").split("?", 1)[0]
    try:
        return UUID(value)
    except ValueError:
        return None


def _payload_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _resolve_current_attempt_number(job_attempt_number: int | None, failed_attempt_number: int | None) -> int | None:
    candidates = [value for value in (job_attempt_number, failed_attempt_number) if value is not None and value >= 1]
    if not candidates:
        return None
    return max(int(value) for value in candidates)


__all__ = ["ManualRetryResult", "ManualRetryService"]
