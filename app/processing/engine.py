"""Processing worker orchestration for WP-08."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from app import ensure_uuid_str
from app.events.outbox import LIFECYCLE_STREAM_NAME, enqueue_event
from app.observability.logging import configure_structured_logging, emit_structured_log
from app.processing.spark_adapter import (
    ProcessingAdapterInput,
    ProcessingAdapterResult,
    SparkDemoAdapter,
)
from app.repositories.delivery import DeliveryRepository
from app.repositories.events import EventOutboxRepository
from app.repositories.jobs import JobRepository
from app.repositories.processing import ProcessingRepository
from app.repositories.stage_claims import StageClaimRepository
from app.repositories.validation import ValidationRepository

LEASE_SECONDS = 30
PROCESSING_STAGE = "processing"
PROCESSOR_SERVICE = "processor"
REASON_JOB_NOT_FOUND = "JOB_NOT_FOUND"
REASON_JOB_NOT_PROCESSABLE = "JOB_NOT_PROCESSABLE"
REASON_JOB_CLAIM_CONFLICT = "JOB_CLAIM_CONFLICT"
REASON_PROCESSING_STARTED = "PROCESSING_STARTED"
REASON_PROCESSING_COMPLETED = "PROCESSING_COMPLETED"
REASON_SOURCE_SHA256_MISSING = "PROCESSING_SOURCE_SHA256_MISSING"
REASON_VALIDATION_NOT_CONFIRMED = "PROCESSING_VALIDATION_NOT_CONFIRMED"
REASON_PROCESSING_UNEXPECTED_ERROR = "PROCESSING_UNEXPECTED_ERROR"


@dataclass(frozen=True, slots=True)
class ProcessingExecutionResult:
    job_id: UUID | str | None
    status: Literal["processed", "failed", "skipped"]
    final_state: str | None
    reason_code: str
    attempt_number: int | None
    event_type: str | None
    error_code: str | None = None
    output_manifest_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ProcessingBatchResult:
    claimed: int
    processed: int
    failed: int
    skipped: int


class ProcessingWorker:
    """Claim validated jobs, run the adapter, persist attempts, and enqueue events."""

    def __init__(
        self,
        *,
        session: Session | None = None,
        processing_repository: ProcessingRepository | None = None,
        stage_claim_repository: StageClaimRepository | None = None,
        job_repository: JobRepository | None = None,
        delivery_repository: DeliveryRepository | None = None,
        event_repository: EventOutboxRepository | None = None,
        validation_repository: ValidationRepository | None = None,
        adapter: SparkDemoAdapter | None = None,
        clock: Callable[[], datetime] | None = None,
        filesystem_resolver: Callable[[str], str] | None = None,
        retry_max_attempts: int = 3,
        logger: logging.Logger | None = None,
    ) -> None:
        if session is None and any(
            dependency is None
            for dependency in (
                processing_repository,
                stage_claim_repository,
                job_repository,
                delivery_repository,
                event_repository,
            )
        ):
            raise ValueError("session or all repository instances are required")

        inferred_session = session or (job_repository.session if job_repository is not None else None)
        if validation_repository is None and inferred_session is None:
            raise ValueError("validation_repository or session is required")

        self.session = inferred_session
        self.processing_repository = processing_repository or ProcessingRepository(inferred_session)
        self.stage_claim_repository = stage_claim_repository or StageClaimRepository(inferred_session)
        self.job_repository = job_repository or JobRepository(inferred_session)
        self.delivery_repository = delivery_repository or DeliveryRepository(inferred_session)
        self.event_repository = event_repository or EventOutboxRepository(inferred_session)
        self.validation_repository = validation_repository or ValidationRepository(inferred_session)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.filesystem_resolver = filesystem_resolver or (lambda locator: locator)
        self.adapter = adapter or SparkDemoAdapter(
            filesystem_resolver=self.filesystem_resolver,
            clock=self.clock,
        )
        self.retry_max_attempts = retry_max_attempts
        self.logger = logger or configure_structured_logging("processor", logger_name="stream_lite.processor")
        self.log_records: list[dict[str, object]] = []

    def process_one(
        self,
        job_id: UUID | str,
        correlation_id: str | None = None,
    ) -> ProcessingExecutionResult:
        job = self.job_repository.get_job(job_id)
        if job is None:
            return ProcessingExecutionResult(
                job_id=str(job_id),
                status="skipped",
                final_state=None,
                reason_code=REASON_JOB_NOT_FOUND,
                attempt_number=None,
                event_type=None,
            )

        resolved_correlation_id = ensure_uuid_str(correlation_id or job.correlation_id, field_name="correlation_id")
        if not _is_processable_state(job.state, job.attempt_number):
            return ProcessingExecutionResult(
                job_id=job.job_id,
                status="skipped",
                final_state=job.state,
                reason_code=REASON_JOB_NOT_PROCESSABLE,
                attempt_number=None,
                event_type=None,
            )
        processing_start_state = job.state

        latest_validation_attempt = self.validation_repository.get_latest_attempt(job.job_id)
        if latest_validation_attempt is None or latest_validation_attempt.validation_status != "valid":
            self._log(
                "processing.validation_not_confirmed",
                "Processing skipped because no successful validation attempt was found.",
                correlation_id=resolved_correlation_id,
                watcher_id=str(job.watcher_id),
                job_id=str(job.job_id),
                error_code=REASON_VALIDATION_NOT_CONFIRMED,
            )
            return ProcessingExecutionResult(
                job_id=job.job_id,
                status="skipped",
                final_state=job.state,
                reason_code=REASON_VALIDATION_NOT_CONFIRMED,
                attempt_number=None,
                event_type=None,
                error_code=REASON_VALIDATION_NOT_CONFIRMED,
            )

        attempt_number = self._resolve_attempt_number(job.attempt_number)
        started_at = self.clock()
        claim_id: UUID | None = None
        processing_attempt_id: UUID | None = None

        self._log(
            "processing.claim_started",
            "Processing claim started.",
            correlation_id=resolved_correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            attempt_number=attempt_number,
        )
        try:
            claim = self.stage_claim_repository.claim_stage(
                job_id=job.job_id,
                stage=PROCESSING_STAGE,
                attempt_number=attempt_number,
                owner_service=PROCESSOR_SERVICE,
                lease_expires_at=started_at + timedelta(seconds=LEASE_SECONDS),
                correlation_id=resolved_correlation_id,
            )
            claim_id = claim.claim_id
        except ValueError:
            self._log(
                "processing.claim_conflict",
                "Processing claim conflict prevented adapter execution.",
                correlation_id=resolved_correlation_id,
                watcher_id=str(job.watcher_id),
                job_id=str(job.job_id),
                attempt_number=attempt_number,
                error_code=REASON_JOB_CLAIM_CONFLICT,
            )
            return ProcessingExecutionResult(
                job_id=job.job_id,
                status="skipped",
                final_state=job.state,
                reason_code=REASON_JOB_CLAIM_CONFLICT,
                attempt_number=attempt_number,
                event_type=None,
            )

        try:
            self.job_repository.update_state(job.job_id, new_state="PROCESSING", attempt_number=attempt_number)
            self.job_repository.append_state_history(
                job_id=job.job_id,
                previous_state=processing_start_state,
                new_state="PROCESSING",
                actor_service=PROCESSOR_SERVICE,
                reason_code=REASON_PROCESSING_STARTED,
                correlation_id=resolved_correlation_id,
                transitioned_at=started_at,
            )
            attempt = self.processing_repository.create_processing_attempt(
                job_id=job.job_id,
                attempt_number=attempt_number,
                engine=self.adapter.engine,
                engine_version=self.adapter.engine_version,
                input_locator=job.source_container_locator,
                started_at=started_at,
                correlation_id=resolved_correlation_id,
                status="started",
            )
            processing_attempt_id = attempt.processing_attempt_id
            enqueue_event(
                self.event_repository,
                stream_name=LIFECYCLE_STREAM_NAME,
                event_payload={
                    "schema_version": "1.0.0",
                    "correlation_id": resolved_correlation_id,
                    "job_id": job.job_id,
                    "watcher_id": job.watcher_id,
                    "attempt_number": attempt_number,
                    "occurred_at": _format_rfc3339(started_at),
                    "producer": PROCESSOR_SERVICE,
                    "event_type": "processing.started",
                    "payload": {
                        "engine": self.adapter.engine,
                        "engine_version": self.adapter.engine_version,
                        "input_locator": job.source_container_locator,
                        "started_at": _format_rfc3339(started_at),
                    },
                },
            )
            self._log(
                "processing.started",
                "Processing started.",
                correlation_id=resolved_correlation_id,
                watcher_id=str(job.watcher_id),
                job_id=str(job.job_id),
                attempt_number=attempt_number,
                state_from=processing_start_state,
                state_to="PROCESSING",
            )

            if not job.source_sha256:
                adapter_result = self._build_worker_failure(
                    input_locator=job.source_container_locator,
                    started_at=started_at,
                    completed_at=self.clock(),
                    error_code=REASON_SOURCE_SHA256_MISSING,
                    retryable=False,
                    operator_message="Processing metadata is missing the source checksum.",
                )
            else:
                adapter_result = self.adapter.run_demo_transform(
                    ProcessingAdapterInput(
                        job_id=job.job_id,
                        watcher_id=job.watcher_id,
                        correlation_id=resolved_correlation_id,
                        input_locator=job.source_container_locator,
                        source_file_name=job.source_file_name,
                        source_extension=job.source_extension,
                        source_sha256=job.source_sha256,
                        started_at=started_at,
                        source_display_path=job.source_display_path,
                    )
                )
        except Exception:
            adapter_result = self._build_worker_failure(
                input_locator=job.source_container_locator,
                started_at=started_at,
                completed_at=self.clock(),
                error_code=REASON_PROCESSING_UNEXPECTED_ERROR,
                retryable=True,
                operator_message="Processing failed unexpectedly.",
            )

        try:
            if adapter_result.status == "processed":
                return self._complete_success(
                    job=job,
                    attempt_number=attempt_number,
                    correlation_id=resolved_correlation_id,
                    processing_attempt_id=processing_attempt_id,
                    adapter_result=adapter_result,
                )
            return self._complete_failure(
                job=job,
                attempt_number=attempt_number,
                correlation_id=resolved_correlation_id,
                processing_attempt_id=processing_attempt_id,
                adapter_result=adapter_result,
            )
        finally:
            if claim_id is not None:
                self.stage_claim_repository.release_stage(claim_id, released_at=self.clock())
                self._log(
                    "processing.claim_released",
                    "Processing claim released.",
                    correlation_id=resolved_correlation_id,
                    watcher_id=str(job.watcher_id),
                    job_id=str(job.job_id),
                    attempt_number=attempt_number,
                )

    def claim_and_process(
        self,
        limit: int = 1,
        correlation_id: str | None = None,
    ) -> ProcessingBatchResult:
        jobs = list(reversed(self.job_repository.list_jobs(state="VALIDATED")))
        retry_ready_jobs = [
            job
            for job in reversed(self.job_repository.list_jobs(state="PROCESSING"))
            if _is_retry_attempt(job.attempt_number)
        ]
        jobs.extend(retry_ready_jobs)
        claimed = 0
        processed = 0
        failed = 0
        skipped = 0

        for job in jobs[: max(limit, 0)]:
            result = self.process_one(job.job_id, correlation_id=correlation_id or str(job.correlation_id))
            if result.status == "processed":
                claimed += 1
                processed += 1
            elif result.status == "failed":
                claimed += 1
                failed += 1
            else:
                skipped += 1

        return ProcessingBatchResult(
            claimed=claimed,
            processed=processed,
            failed=failed,
            skipped=skipped,
        )

    def _complete_success(
        self,
        *,
        job,
        attempt_number: int,
        correlation_id: str,
        processing_attempt_id: UUID | None,
        adapter_result: ProcessingAdapterResult,
    ) -> ProcessingExecutionResult:
        if processing_attempt_id is None:
            raise ValueError("processing attempt id is required for success completion")
        if adapter_result.output_locator is None or adapter_result.summary_locator is None or adapter_result.manifest_locator is None:
            raise ValueError("processed adapter results must include artifact locators")
        if adapter_result.output_manifest_id is None:
            raise ValueError("processed adapter results must include an output manifest id")

        self.delivery_repository.create_output_manifest(
            output_manifest_id=adapter_result.output_manifest_id,
            job_id=job.job_id,
            watcher_id=job.watcher_id,
            schema_version="1.0.0",
            manifest_locator=adapter_result.manifest_locator,
            processing_summary_locator=adapter_result.summary_locator,
            produced_output_locators=[adapter_result.output_locator],
            source_sha256=job.source_sha256,
            destination_outcomes=[],
            finalized_at=adapter_result.completed_at,
            status="processed",
            correlation_id=correlation_id,
        )
        self.processing_repository.complete_processing_attempt(
            processing_attempt_id,
            output_locator=adapter_result.output_locator,
            summary_locator=adapter_result.summary_locator,
            completed_at=adapter_result.completed_at,
            duration_seconds=float(adapter_result.duration_seconds),
            row_count=adapter_result.row_count,
            record_count=adapter_result.record_count,
            byte_count=adapter_result.byte_count,
        )
        self.job_repository.update_state(job.job_id, new_state="PROCESSED", attempt_number=attempt_number)
        self.job_repository.append_state_history(
            job_id=job.job_id,
            previous_state="PROCESSING",
            new_state="PROCESSED",
            actor_service=PROCESSOR_SERVICE,
            reason_code=REASON_PROCESSING_COMPLETED,
            correlation_id=correlation_id,
            transitioned_at=adapter_result.completed_at,
        )
        enqueue_event(
            self.event_repository,
            stream_name=LIFECYCLE_STREAM_NAME,
            event_payload={
                "schema_version": "1.0.0",
                "correlation_id": correlation_id,
                "job_id": job.job_id,
                "watcher_id": job.watcher_id,
                "attempt_number": attempt_number,
                "occurred_at": _format_rfc3339(adapter_result.completed_at),
                "producer": PROCESSOR_SERVICE,
                "event_type": "processing.completed",
                "payload": {
                    "engine": adapter_result.engine,
                    "output_manifest_id": adapter_result.output_manifest_id,
                    "output_locator": adapter_result.output_locator,
                    "input_rows": adapter_result.row_count,
                    "output_rows": adapter_result.row_count,
                    "duration_seconds": float(adapter_result.duration_seconds),
                },
            },
        )
        self._log(
            "processing.completed",
            "Processing completed.",
            correlation_id=correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            attempt_number=attempt_number,
            duration_seconds=adapter_result.duration_seconds,
            state_from="PROCESSING",
            state_to="PROCESSED",
        )
        return ProcessingExecutionResult(
            job_id=job.job_id,
            status="processed",
            final_state="PROCESSED",
            reason_code=REASON_PROCESSING_COMPLETED,
            attempt_number=attempt_number,
            event_type="processing.completed",
            output_manifest_id=adapter_result.output_manifest_id,
        )

    def _complete_failure(
        self,
        *,
        job,
        attempt_number: int,
        correlation_id: str,
        processing_attempt_id: UUID | None,
        adapter_result: ProcessingAdapterResult,
    ) -> ProcessingExecutionResult:
        error_code = adapter_result.error_code or REASON_PROCESSING_UNEXPECTED_ERROR
        if processing_attempt_id is not None:
            self.processing_repository.fail_processing_attempt(
                processing_attempt_id,
                error_code=error_code,
                completed_at=adapter_result.completed_at,
                duration_seconds=float(adapter_result.duration_seconds),
            )
        next_state = (
            "RETRY_PENDING"
            if adapter_result.retryable and attempt_number < self.retry_max_attempts
            else "FAILED"
        )
        self.job_repository.update_state(
            job.job_id,
            new_state=next_state,
            latest_error_code=error_code,
            attempt_number=attempt_number,
        )
        self.job_repository.append_state_history(
            job_id=job.job_id,
            previous_state="PROCESSING",
            new_state=next_state,
            actor_service=PROCESSOR_SERVICE,
            reason_code=error_code,
            correlation_id=correlation_id,
            transitioned_at=adapter_result.completed_at,
        )
        enqueue_event(
            self.event_repository,
            stream_name=LIFECYCLE_STREAM_NAME,
            event_payload={
                "schema_version": "1.0.0",
                "correlation_id": correlation_id,
                "job_id": job.job_id,
                "watcher_id": job.watcher_id,
                "attempt_number": attempt_number,
                "occurred_at": _format_rfc3339(adapter_result.completed_at),
                "producer": PROCESSOR_SERVICE,
                "event_type": "processing.failed",
                "payload": {
                    "engine": adapter_result.engine,
                    "failure_class": "retryable" if adapter_result.retryable else "non_retryable",
                    "error_code": error_code,
                    "operator_message": adapter_result.operator_message,
                    "retryable": adapter_result.retryable,
                },
            },
        )
        self._log(
            "processing.failed",
            "Processing failed.",
            level="WARNING",
            correlation_id=correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            attempt_number=attempt_number,
            duration_seconds=adapter_result.duration_seconds,
            state_from="PROCESSING",
            state_to=next_state,
            error_code=error_code,
        )
        return ProcessingExecutionResult(
            job_id=job.job_id,
            status="failed",
            final_state=next_state,
            reason_code=error_code,
            attempt_number=attempt_number,
            event_type="processing.failed",
            error_code=error_code,
        )

    def _build_worker_failure(
        self,
        *,
        input_locator: str,
        started_at: datetime,
        completed_at: datetime,
        error_code: str,
        retryable: bool,
        operator_message: str,
    ) -> ProcessingAdapterResult:
        return ProcessingAdapterResult(
            status="failed",
            engine=self.adapter.engine,
            engine_version=self.adapter.engine_version,
            input_locator=input_locator,
            output_locator=None,
            summary_locator=None,
            manifest_locator=None,
            output_manifest_id=None,
            row_count=None,
            record_count=None,
            byte_count=None,
            bytes_written=None,
            started_at=_as_utc(started_at),
            completed_at=_as_utc(completed_at),
            duration_seconds=_duration_seconds(started_at, completed_at),
            error_code=error_code,
            retryable=retryable,
            operator_message=operator_message,
        )

    def _log(
        self,
        event: str,
        message: str,
        *,
        correlation_id: str,
        level: str = "INFO",
        **fields: object,
    ) -> None:
        record = emit_structured_log(
            self.logger,
            service="processor",
            component="processing.worker",
            event=event,
            message=message,
            level=level,
            correlation_id=correlation_id,
            **fields,
        )
        self.log_records.append(record)

    @staticmethod
    def _resolve_attempt_number(value: int | None) -> int:
        if value is None or value < 1:
            return 1
        return int(value)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_rfc3339(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _is_retry_attempt(attempt_number: int | None) -> bool:
    return attempt_number is not None and attempt_number > 1


def _is_processable_state(state: str, attempt_number: int | None) -> bool:
    return state == "VALIDATED" or (state == "PROCESSING" and _is_retry_attempt(attempt_number))


def _duration_seconds(started_at: datetime, completed_at: datetime) -> int:
    delta = (_as_utc(completed_at) - _as_utc(started_at)).total_seconds()
    return max(0, int(delta))


__all__ = [
    "ProcessingBatchResult",
    "ProcessingExecutionResult",
    "ProcessingWorker",
]
