"""Validation-stage orchestration for WP-07."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping
from uuid import UUID

from pydantic import ValidationError

from app import ensure_uuid_str
from app.events.models import JobRegisteredEvent
from app.events.outbox import LIFECYCLE_STREAM_NAME, enqueue_event
from app.observability.logging import configure_structured_logging, emit_structured_log
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.validation import ValidationRepository

from .quarantine import QuarantineService
from .validator import FileValidator


@dataclass(frozen=True, slots=True)
class ValidationExecutionResult:
    job_id: UUID
    final_state: str
    status: str
    attempt_number: int | None
    event_type: str | None
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    processed_jobs: int
    skipped_existing_attempts: int
    skipped_non_registered: int


class ValidationService:
    """Coordinate validation attempts, state transitions, quarantine, and events."""

    def __init__(
        self,
        *,
        job_repository: JobRepository,
        file_repository: FileRepository,
        validation_repository: ValidationRepository,
        event_repository: EventOutboxRepository,
        validator: FileValidator,
        quarantine_service: QuarantineService,
        now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.file_repository = file_repository
        self.validation_repository = validation_repository
        self.event_repository = event_repository
        self.validator = validator
        self.quarantine_service = quarantine_service
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.monotonic = monotonic or time.monotonic
        self.logger = logger or configure_structured_logging("validator", logger_name="stream_lite.validator")
        self.log_records: list[dict[str, object]] = quarantine_service.log_records

    def validate_registered_job(
        self,
        job_id: UUID | str,
        correlation_id: str | None = None,
    ) -> ValidationExecutionResult:
        job = self.job_repository.get_job(job_id)
        if job is None:
            raise ValueError("job not found")
        file_record = self.file_repository.get_file_record(job.file_id)
        if file_record is None:
            raise ValueError("file record not found")

        resolved_correlation_id = ensure_uuid_str(correlation_id or job.correlation_id, field_name="correlation_id")
        if job.state != "REGISTERED":
            return ValidationExecutionResult(
                job_id=job.job_id,
                final_state=job.state,
                status="skipped_non_registered",
                attempt_number=None,
                event_type=None,
            )

        existing_attempt = self.validation_repository.get_latest_attempt(job.job_id)
        if existing_attempt is not None:
            return ValidationExecutionResult(
                job_id=job.job_id,
                final_state=job.state,
                status="skipped_existing_attempt",
                attempt_number=existing_attempt.attempt_number,
                event_type=None,
                reason_codes=tuple(existing_attempt.reason_codes),
            )

        attempt_number = 1
        started_at = self.now()
        started = self.monotonic()
        self._log(
            "validation.started",
            "Validation attempt started.",
            correlation_id=resolved_correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            source_display_path=job.source_display_path,
        )
        self.job_repository.update_state(job.job_id, new_state="VALIDATING", attempt_number=attempt_number)
        self.job_repository.append_state_history(
            job_id=job.job_id,
            previous_state="REGISTERED",
            new_state="VALIDATING",
            actor_service="validator",
            reason_code="VALIDATION_STARTED",
            correlation_id=resolved_correlation_id,
            transitioned_at=started_at,
        )

        validation_result = self.validator.validate_file(
            job.source_container_locator,
            source_display_path=job.source_display_path,
            correlation_id=resolved_correlation_id,
        )
        completed_at = self.now()
        attempt = self.validation_repository.create_validation_attempt(
            job_id=job.job_id,
            attempt_number=attempt_number,
            validation_status=validation_result.status,
            rules_applied=list(validation_result.rules_applied),
            reason_codes=list(validation_result.reason_codes),
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=validation_result.duration_seconds,
            correlation_id=resolved_correlation_id,
        )

        if validation_result.is_valid:
            self.job_repository.update_state(job.job_id, new_state="VALIDATED", attempt_number=attempt_number)
            self.job_repository.append_state_history(
                job_id=job.job_id,
                previous_state="VALIDATING",
                new_state="VALIDATED",
                actor_service="validator",
                reason_code="VALIDATION_PASSED",
                correlation_id=resolved_correlation_id,
                transitioned_at=completed_at,
            )
            enqueue_event(
                self.event_repository,
                stream_name=LIFECYCLE_STREAM_NAME,
                event_payload={
                    "schema_version": "1.0.0",
                    "correlation_id": resolved_correlation_id,
                    "job_id": job.job_id,
                    "watcher_id": job.watcher_id,
                    "attempt_number": attempt_number,
                    "occurred_at": _format_rfc3339(completed_at),
                    "producer": "validator",
                    "event_type": "file.validated",
                    "payload": {
                        "file_id": file_record.file_id,
                        "validation_status": "valid",
                        "rules_applied": list(validation_result.rules_applied),
                        "duration_seconds": validation_result.duration_seconds,
                    },
                },
            )
            self._log(
                "validation.validated",
                "Validation completed successfully.",
                correlation_id=resolved_correlation_id,
                watcher_id=str(job.watcher_id),
                job_id=str(job.job_id),
                duration_ms=self._duration_ms(started),
                state_from="VALIDATING",
                state_to="VALIDATED",
            )
            self._log(
                "validation.completed",
                "Validation flow completed.",
                correlation_id=resolved_correlation_id,
                watcher_id=str(job.watcher_id),
                job_id=str(job.job_id),
                duration_ms=self._duration_ms(started),
                state_from="REGISTERED",
                state_to="VALIDATED",
            )
            return ValidationExecutionResult(
                job_id=job.job_id,
                final_state="VALIDATED",
                status="validated",
                attempt_number=attempt_number,
                event_type="file.validated",
            )

        primary_reason_code = validation_result.primary_reason_code or "SCHEMA_INVALID"
        self.job_repository.update_state(
            job.job_id,
            new_state="INVALID",
            latest_error_code=primary_reason_code,
            attempt_number=attempt_number,
        )
        self.job_repository.append_state_history(
            job_id=job.job_id,
            previous_state="VALIDATING",
            new_state="INVALID",
            actor_service="validator",
            reason_code=primary_reason_code,
            correlation_id=resolved_correlation_id,
            transitioned_at=completed_at,
        )
        self._log(
            "validation.invalid",
            "Validation rejected the source file.",
            correlation_id=resolved_correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            duration_ms=self._duration_ms(started),
            state_from="VALIDATING",
            state_to="INVALID",
            error_code=primary_reason_code,
            source_display_path=job.source_display_path,
            reason_codes=list(validation_result.reason_codes),
        )

        quarantine_result = self.quarantine_service.quarantine_file(
            job_id=job.job_id,
            watcher_id=job.watcher_id,
            source_container_locator=job.source_container_locator,
            source_display_path=job.source_display_path,
            source_file_name=job.source_file_name,
            source_sha256=job.source_sha256 or file_record.sha256 or ("0" * 64),
            reason_codes=list(validation_result.reason_codes),
            operator_message=validation_result.operator_message,
            correlation_id=resolved_correlation_id,
        )
        quarantine_record = self.validation_repository.create_quarantine_record(
            job_id=job.job_id,
            file_id=file_record.file_id,
            watcher_id=job.watcher_id,
            validation_attempt_id=attempt.validation_attempt_id,
            schema_version="1.0.0",
            source_display_path=job.source_display_path,
            source_sha256=job.source_sha256 or file_record.sha256,
            quarantine_locator=quarantine_result.quarantine_locator,
            quarantine_display_path=quarantine_result.quarantine_display_path,
            reason_code=primary_reason_code,
            copy_status=quarantine_result.copy_status,
            checksum_sha256=quarantine_result.checksum_sha256,
            copied_size_bytes=quarantine_result.copied_size_bytes,
            operator_message=validation_result.operator_message,
            correlation_id=resolved_correlation_id,
        )
        self.job_repository.update_state(
            job.job_id,
            new_state="QUARANTINED",
            latest_error_code=primary_reason_code,
            attempt_number=attempt_number,
        )
        self.job_repository.append_state_history(
            job_id=job.job_id,
            previous_state="INVALID",
            new_state="QUARANTINED",
            actor_service="validator",
            reason_code=primary_reason_code,
            correlation_id=resolved_correlation_id,
            transitioned_at=quarantine_result.created_at,
        )
        enqueue_event(
            self.event_repository,
            stream_name=LIFECYCLE_STREAM_NAME,
            event_payload={
                "schema_version": "1.0.0",
                "correlation_id": resolved_correlation_id,
                "job_id": job.job_id,
                "watcher_id": job.watcher_id,
                "attempt_number": attempt_number,
                "occurred_at": _format_rfc3339(quarantine_result.created_at),
                "producer": "validator",
                "event_type": "file.quarantined",
                "payload": {
                    "file_id": file_record.file_id,
                    "validation_status": "quarantined",
                    "reason_codes": list(validation_result.reason_codes),
                    "quarantine_record_id": quarantine_record.quarantine_record_id,
                    "quarantine_locator": quarantine_result.quarantine_locator,
                    "operator_message": validation_result.operator_message,
                },
            },
        )
        self._log(
            "validation.completed",
            "Validation flow completed.",
            correlation_id=resolved_correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            duration_ms=self._duration_ms(started),
            state_from="REGISTERED",
            state_to="QUARANTINED",
            error_code=primary_reason_code,
        )
        return ValidationExecutionResult(
            job_id=job.job_id,
            final_state="QUARANTINED",
            status="quarantined",
            attempt_number=attempt_number,
            event_type="file.quarantined",
            reason_codes=tuple(validation_result.reason_codes),
        )

    def handle_job_registered_event(
        self,
        event_payload: Mapping[str, object],
    ) -> ValidationExecutionResult | None:
        try:
            event = JobRegisteredEvent.model_validate(event_payload)
        except ValidationError:
            return None
        if event.event_type != "job.registered" or event.job_id is None:
            return None
        try:
            return self.validate_registered_job(event.job_id, correlation_id=str(event.correlation_id))
        except ValueError:
            return None

    def reconcile_once(
        self,
        limit: int = 100,
        correlation_id: str | None = None,
    ) -> ReconcileResult:
        processed_jobs = 0
        skipped_existing_attempts = 0
        skipped_non_registered = 0
        for job in self.job_repository.list_jobs(state="REGISTERED")[:limit]:
            if self.validation_repository.get_latest_attempt(job.job_id) is not None:
                skipped_existing_attempts += 1
                continue
            result = self.validate_registered_job(job.job_id, correlation_id=correlation_id or str(job.correlation_id))
            if result.status == "skipped_non_registered":
                skipped_non_registered += 1
                continue
            if result.status == "skipped_existing_attempt":
                skipped_existing_attempts += 1
                continue
            processed_jobs += 1
        return ReconcileResult(
            processed_jobs=processed_jobs,
            skipped_existing_attempts=skipped_existing_attempts,
            skipped_non_registered=skipped_non_registered,
        )

    def _duration_ms(self, started: float) -> int:
        return max(0, int((self.monotonic() - started) * 1000))

    def _log(self, event: str, message: str, *, correlation_id: str, **fields: object) -> None:
        record = emit_structured_log(
            self.logger,
            service="validator",
            component="validation.service",
            event=event,
            message=message,
            correlation_id=correlation_id,
            allowed_container_roots=(
                self.quarantine_service.settings.watch_root,
                self.quarantine_service.settings.output_root,
                self.quarantine_service.settings.quarantine_root,
            ),
            **fields,
        )
        self.log_records.append(record)


def _format_rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["ReconcileResult", "ValidationExecutionResult", "ValidationService"]
