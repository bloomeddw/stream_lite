"""Delivery worker orchestration for WP-09."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Literal
from uuid import UUID

import sqlalchemy as sa
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import ensure_uuid_str, generate_uuid
from app.artifacts import OutputManifest
from app.config.path_policy import PathPolicy
from app.db.models import OutputManifestModel
from app.delivery.filesystem import (
    OutputManifestWriter,
    SOURCE_TRANSFER_FAILED,
    build_destination_outcome,
    build_output_manifest,
    copy_output_to_destination,
)
from app.delivery.routing import DeliveryRouteResolution, resolve_delivery_targets
from app.events.outbox import LIFECYCLE_STREAM_NAME, enqueue_event, _parse_rfc3339_utc
from app.observability.logging import configure_structured_logging, emit_structured_log
from app.repositories.delivery import DeliveryRepository
from app.repositories.events import EventOutboxRepository
from app.repositories.jobs import JobRepository
from app.repositories.stage_claims import StageClaimRepository
from app.repositories.watchers import WatcherRepository

LEASE_SECONDS = 30
DELIVERY_STAGE = "delivery"
DELIVERY_SERVICE = "delivery"
REASON_DELIVERY_STARTED = "DELIVERY_STARTED"
REASON_DELIVERY_COMPLETED = "DELIVERY_COMPLETED"
REASON_JOB_COMPLETED = "JOB_COMPLETED"
REASON_JOB_NOT_CLAIMED = "JOB_CLAIM_CONFLICT"
REASON_JOB_NOT_DELIVERABLE = "JOB_NOT_DELIVERABLE"
REASON_JOB_NOT_FOUND = "JOB_NOT_FOUND"
REASON_OUTPUT_MANIFEST_NOT_FOUND = "OUTPUT_MANIFEST_NOT_FOUND"
REASON_OUTPUT_MANIFEST_INVALID = "OUTPUT_MANIFEST_NOT_FOUND"
REASON_NO_MATCHING_DESTINATION = "NO_MATCHING_DESTINATION"


@dataclass(frozen=True, slots=True)
class DeliveryWorkerResult:
    job_id: UUID | str | None
    status: Literal["delivered", "failed", "skipped"]
    final_state: str | None
    reason_code: str
    attempt_number: int | None
    event_type: str | None
    output_manifest_id: UUID | None = None
    successful_destination_count: int = 0
    failed_destination_count: int = 0


@dataclass(frozen=True, slots=True)
class DeliveryBatchResult:
    claimed: int
    delivered: int
    failed: int
    skipped: int


class DeliveryWorker:
    """Claim processed jobs, fan out delivery attempts, and finalize job state."""

    def __init__(
        self,
        *,
        session: Session | None = None,
        delivery_repository: DeliveryRepository | None = None,
        job_repository: JobRepository | None = None,
        stage_claim_repository: StageClaimRepository | None = None,
        watcher_repository: WatcherRepository | None = None,
        event_repository: EventOutboxRepository | None = None,
        path_policy: PathPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        filesystem_resolver: Callable[[str], str | Path] | None = None,
        retry_max_attempts: int = 3,
        logger: logging.Logger | None = None,
    ) -> None:
        if session is None and any(
            dependency is None
            for dependency in (
                delivery_repository,
                job_repository,
                stage_claim_repository,
                watcher_repository,
                event_repository,
            )
        ):
            raise ValueError("session or all repository instances are required")
        if path_policy is None:
            raise ValueError("path_policy is required")

        inferred_session = session or next(
            repository.session
            for repository in (
                delivery_repository,
                job_repository,
                stage_claim_repository,
                watcher_repository,
                event_repository,
            )
            if repository is not None
        )

        self.session = inferred_session
        self.delivery_repository = delivery_repository or DeliveryRepository(inferred_session)
        self.job_repository = job_repository or JobRepository(inferred_session)
        self.stage_claim_repository = stage_claim_repository or StageClaimRepository(inferred_session)
        self.watcher_repository = watcher_repository or WatcherRepository(inferred_session)
        self.event_repository = event_repository or EventOutboxRepository(inferred_session)
        self.path_policy = path_policy
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.filesystem_resolver = filesystem_resolver or (lambda locator: locator)
        self.retry_max_attempts = retry_max_attempts
        self.output_manifest_writer = OutputManifestWriter(filesystem_resolver=self.filesystem_resolver)
        self.logger = logger or configure_structured_logging("delivery", logger_name="stream_lite.delivery")
        self.log_records: list[dict[str, object]] = []

    def deliver_one(
        self,
        job_id: UUID | str,
        correlation_id: str | None = None,
    ) -> DeliveryWorkerResult:
        job = self.job_repository.get_job(job_id)
        if job is None:
            return DeliveryWorkerResult(
                job_id=str(job_id),
                status="skipped",
                final_state=None,
                reason_code=REASON_JOB_NOT_FOUND,
                attempt_number=None,
                event_type=None,
            )

        resolved_correlation_id = ensure_uuid_str(correlation_id or job.correlation_id, field_name="correlation_id")
        if not _is_deliverable_state(job.state, job.attempt_number):
            return DeliveryWorkerResult(
                job_id=job.job_id,
                status="skipped",
                final_state=job.state,
                reason_code=REASON_JOB_NOT_DELIVERABLE,
                attempt_number=None,
                event_type=None,
            )
        delivery_start_state = job.state

        attempt_number = self._resolve_attempt_number(job.attempt_number)
        processed_manifest_row = self._get_latest_processed_manifest(job.job_id)
        if processed_manifest_row is None:
            return DeliveryWorkerResult(
                job_id=job.job_id,
                status="skipped",
                final_state=job.state,
                reason_code=REASON_OUTPUT_MANIFEST_NOT_FOUND,
                attempt_number=attempt_number,
                event_type=None,
            )

        processed_manifest = self._load_output_manifest(processed_manifest_row.manifest_locator)
        if processed_manifest is None or not processed_manifest.produced_output_locators:
            return DeliveryWorkerResult(
                job_id=job.job_id,
                status="skipped",
                final_state=job.state,
                reason_code=REASON_OUTPUT_MANIFEST_INVALID,
                attempt_number=attempt_number,
                event_type=None,
            )

        route_resolution, source_route_tags = self._resolve_targets(job.watcher_id, job.source_folder_id)
        if not route_resolution.targets:
            return self._fail_without_delivery_targets(
                job=job,
                attempt_number=attempt_number,
                correlation_id=resolved_correlation_id,
                processed_manifest_row=processed_manifest_row,
                processed_manifest=processed_manifest,
                source_route_tags=source_route_tags,
                delivery_start_state=delivery_start_state,
            )

        claim_started_at = self.clock()
        self._log(
            "delivery.claim_started",
            "Delivery claim started.",
            correlation_id=resolved_correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            attempt_number=attempt_number,
        )

        claim_id: UUID | None = None
        final_output_manifest_id = generate_uuid()
        try:
            claim = self.stage_claim_repository.claim_stage(
                job_id=job.job_id,
                stage=DELIVERY_STAGE,
                attempt_number=attempt_number,
                owner_service=DELIVERY_SERVICE,
                lease_expires_at=claim_started_at + timedelta(seconds=LEASE_SECONDS),
                correlation_id=resolved_correlation_id,
            )
            claim_id = claim.claim_id
        except ValueError:
            self._log(
                "delivery.claim_conflict",
                "Delivery claim conflict prevented copy side effects.",
                level="WARNING",
                correlation_id=resolved_correlation_id,
                watcher_id=str(job.watcher_id),
                job_id=str(job.job_id),
                attempt_number=attempt_number,
                error_code=REASON_JOB_NOT_CLAIMED,
            )
            return DeliveryWorkerResult(
                job_id=job.job_id,
                status="skipped",
                final_state=job.state,
                reason_code=REASON_JOB_NOT_CLAIMED,
                attempt_number=attempt_number,
                event_type=None,
            )

        try:
            self.job_repository.update_state(
                job.job_id,
                new_state="DELIVERING",
                attempt_number=attempt_number,
            )
            self.job_repository.append_state_history(
                job_id=job.job_id,
                previous_state=delivery_start_state,
                new_state="DELIVERING",
                actor_service=DELIVERY_SERVICE,
                reason_code=REASON_DELIVERY_STARTED,
                correlation_id=resolved_correlation_id,
                transitioned_at=claim_started_at,
            )

            source_output_locator = processed_manifest.produced_output_locators[0]
            destination_outcomes: list[dict[str, object]] = []
            failed_reason_codes: list[str] = []
            successful_destination_count = 0
            failed_destination_count = 0

            for target in route_resolution.targets:
                destination_started_at = self.clock()
                finalized_locator = _build_finalized_locator(
                    destination_root_locator=target.destination_container_locator,
                    watcher_id=job.watcher_id,
                    job_id=job.job_id,
                    as_of_date=destination_started_at.date(),
                    source_output_locator=source_output_locator,
                )
                temporary_locator = _build_temporary_locator(finalized_locator)
                attempt = self.delivery_repository.create_delivery_attempt(
                    job_id=job.job_id,
                    destination_folder_id=target.destination_folder_id,
                    attempt_number=attempt_number,
                    matched_route_tags=list(target.matched_route_tags),
                    started_at=destination_started_at,
                    correlation_id=resolved_correlation_id,
                    status="started",
                    temporary_locator=temporary_locator,
                )
                enqueue_event(
                    self.event_repository,
                    stream_name=LIFECYCLE_STREAM_NAME,
                    idempotency_key=_delivery_idempotency_key(
                        "delivery.started",
                        job.job_id,
                        target.destination_folder_id,
                        attempt_number,
                    ),
                    event_payload={
                        "schema_version": "1.0.0",
                        "correlation_id": resolved_correlation_id,
                        "job_id": job.job_id,
                        "watcher_id": job.watcher_id,
                        "attempt_number": attempt_number,
                        "occurred_at": _format_rfc3339(destination_started_at),
                        "producer": DELIVERY_SERVICE,
                        "event_type": "delivery.started",
                        "payload": {
                            "destination_folder_id": target.destination_folder_id,
                            "destination_display_path": target.destination_display_path,
                            "matched_tags": list(target.matched_route_tags),
                            "output_manifest_id": final_output_manifest_id,
                            "started_at": _format_rfc3339(destination_started_at),
                        },
                    },
                )
                self._log(
                    "delivery.started",
                    "Delivery attempt started.",
                    correlation_id=resolved_correlation_id,
                    watcher_id=str(job.watcher_id),
                    job_id=str(job.job_id),
                    attempt_number=attempt_number,
                    destination_folder_id=str(target.destination_folder_id),
                    destination_display_path=target.destination_display_path,
                    matched_route_tags=list(target.matched_route_tags),
                )

                copy_result = copy_output_to_destination(
                    source_output_locator=source_output_locator,
                    destination_root_locator=target.destination_container_locator,
                    watcher_id=job.watcher_id,
                    job_id=job.job_id,
                    as_of_date=destination_started_at.date(),
                    filesystem_resolver=self.filesystem_resolver,
                    path_policy=self.path_policy,
                )
                destination_completed_at = self.clock()
                duration_seconds = _duration_seconds(destination_started_at, destination_completed_at)
                duration_ms = max(0, int(duration_seconds * 1000))

                if copy_result.status == "delivered":
                    successful_destination_count += 1
                    destination_outcomes.append(
                        build_destination_outcome(
                            destination_folder_id=target.destination_folder_id,
                            destination_display_path=target.destination_display_path,
                            matched_route_tags=target.matched_route_tags,
                            status="delivered",
                            finalized_locator=copy_result.finalized_locator,
                            checksum_sha256=copy_result.checksum_sha256,
                            bytes_written=copy_result.bytes_written,
                        )
                    )
                    self.delivery_repository.complete_delivery_attempt(
                        attempt.delivery_attempt_id,
                        finalized_locator=copy_result.finalized_locator or finalized_locator,
                        manifest_locator=processed_manifest_row.manifest_locator,
                        checksum_sha256=copy_result.checksum_sha256 or processed_manifest.source_sha256,
                        completed_at=destination_completed_at,
                    )
                    enqueue_event(
                        self.event_repository,
                        stream_name=LIFECYCLE_STREAM_NAME,
                        idempotency_key=_delivery_idempotency_key(
                            "delivery.completed",
                            job.job_id,
                            target.destination_folder_id,
                            attempt_number,
                        ),
                        event_payload={
                            "schema_version": "1.0.0",
                            "correlation_id": resolved_correlation_id,
                            "job_id": job.job_id,
                            "watcher_id": job.watcher_id,
                            "attempt_number": attempt_number,
                            "occurred_at": _format_rfc3339(destination_completed_at),
                            "producer": DELIVERY_SERVICE,
                            "event_type": "delivery.completed",
                            "payload": {
                                "destination_folder_id": target.destination_folder_id,
                                "destination_display_path": target.destination_display_path,
                                "output_manifest_id": final_output_manifest_id,
                                "bytes_written": copy_result.bytes_written,
                                "completed_at": _format_rfc3339(destination_completed_at),
                                "duration_seconds": duration_seconds,
                            },
                        },
                    )
                    self._log(
                        "delivery.completed",
                        "Delivery attempt completed.",
                        correlation_id=resolved_correlation_id,
                        watcher_id=str(job.watcher_id),
                        job_id=str(job.job_id),
                        attempt_number=attempt_number,
                        destination_folder_id=str(target.destination_folder_id),
                        destination_display_path=target.destination_display_path,
                        matched_route_tags=list(target.matched_route_tags),
                        duration_ms=duration_ms,
                    )
                    continue

                failed_destination_count += 1
                error_code = copy_result.reason_code or "FINALIZE_FAILED"
                failed_reason_codes.append(error_code)
                self._record_transfer_health_failure(
                    job=job,
                    destination_folder_id=target.destination_folder_id,
                    reason_code=error_code,
                )
                destination_outcomes.append(
                    build_destination_outcome(
                        destination_folder_id=target.destination_folder_id,
                        destination_display_path=target.destination_display_path,
                        matched_route_tags=target.matched_route_tags,
                        status="failed",
                        bytes_written=copy_result.bytes_written or None,
                        reason_code=error_code,
                        retryable=copy_result.retryable,
                    )
                )
                self.delivery_repository.fail_delivery_attempt(
                    attempt.delivery_attempt_id,
                    failure_code=error_code,
                    completed_at=destination_completed_at,
                    manifest_locator=processed_manifest_row.manifest_locator,
                )
                enqueue_event(
                    self.event_repository,
                    stream_name=LIFECYCLE_STREAM_NAME,
                    idempotency_key=_delivery_idempotency_key(
                        "delivery.failed",
                        job.job_id,
                        target.destination_folder_id,
                        attempt_number,
                    ),
                    event_payload={
                        "schema_version": "1.0.0",
                        "correlation_id": resolved_correlation_id,
                        "job_id": job.job_id,
                        "watcher_id": job.watcher_id,
                        "attempt_number": attempt_number,
                        "occurred_at": _format_rfc3339(destination_completed_at),
                        "producer": DELIVERY_SERVICE,
                        "event_type": "delivery.failed",
                        "payload": {
                            "destination_folder_id": target.destination_folder_id,
                            "destination_display_path": target.destination_display_path,
                            "failure_class": "retryable" if copy_result.retryable else "non_retryable",
                            "error_code": error_code,
                            "operator_message": copy_result.operator_message,
                            "retryable": copy_result.retryable,
                        },
                    },
                )
                self._log(
                    "delivery.failed",
                    "Delivery attempt failed.",
                    level="WARNING",
                    correlation_id=resolved_correlation_id,
                    watcher_id=str(job.watcher_id),
                    job_id=str(job.job_id),
                    attempt_number=attempt_number,
                    destination_folder_id=str(target.destination_folder_id),
                    destination_display_path=target.destination_display_path,
                    matched_route_tags=list(target.matched_route_tags),
                    duration_ms=duration_ms,
                    error_code=error_code,
                    operator_message=copy_result.operator_message,
                )

            finalized_at = self.clock()
            final_state, manifest_status, final_reason_code = self._final_state_from_outcomes(
                destination_outcomes=destination_outcomes,
                attempt_number=attempt_number,
            )
            latest_error_code = failed_reason_codes[0] if failed_reason_codes else None

            if final_state == "COMPLETED":
                self.job_repository.update_state(
                    job.job_id,
                    new_state="DELIVERED",
                    attempt_number=attempt_number,
                )
                self.job_repository.append_state_history(
                    job_id=job.job_id,
                    previous_state="DELIVERING",
                    new_state="DELIVERED",
                    actor_service=DELIVERY_SERVICE,
                    reason_code=REASON_DELIVERY_COMPLETED,
                    correlation_id=resolved_correlation_id,
                    transitioned_at=finalized_at,
                )
                self.job_repository.update_state(
                    job.job_id,
                    new_state="COMPLETED",
                    attempt_number=attempt_number,
                )
                self.job_repository.append_state_history(
                    job_id=job.job_id,
                    previous_state="DELIVERED",
                    new_state="COMPLETED",
                    actor_service=DELIVERY_SERVICE,
                    reason_code=REASON_JOB_COMPLETED,
                    correlation_id=resolved_correlation_id,
                    transitioned_at=finalized_at,
                )
            else:
                self.job_repository.update_state(
                    job.job_id,
                    new_state=final_state,
                    latest_error_code=latest_error_code,
                    attempt_number=attempt_number,
                )
                self.job_repository.append_state_history(
                    job_id=job.job_id,
                    previous_state="DELIVERING",
                    new_state=final_state,
                    actor_service=DELIVERY_SERVICE,
                    reason_code=final_reason_code,
                    correlation_id=resolved_correlation_id,
                    transitioned_at=finalized_at,
                )

            final_manifest = build_output_manifest(
                existing_manifest=processed_manifest,
                destination_outcomes=destination_outcomes,
                status=manifest_status,
                completed_at=_format_rfc3339(finalized_at),
                created_at=_format_rfc3339(finalized_at),
                correlation_id=resolved_correlation_id,
                duration_seconds=_manifest_duration_seconds(processed_manifest.started_at, finalized_at),
            )
            self.output_manifest_writer.write_manifest(
                manifest_locator=processed_manifest_row.manifest_locator,
                manifest=final_manifest,
            )
            self.delivery_repository.create_output_manifest(
                output_manifest_id=final_output_manifest_id,
                job_id=job.job_id,
                watcher_id=job.watcher_id,
                schema_version=processed_manifest_row.schema_version,
                manifest_locator=processed_manifest_row.manifest_locator,
                processing_summary_locator=processed_manifest_row.processing_summary_locator,
                produced_output_locators=list(processed_manifest_row.produced_output_locators),
                source_sha256=processed_manifest_row.source_sha256,
                output_sha256=processed_manifest_row.output_sha256,
                destination_outcomes=[dict(outcome) for outcome in destination_outcomes],
                finalized_at=finalized_at,
                status=manifest_status,
                correlation_id=resolved_correlation_id,
            )
            self._log(
                "delivery.manifest_written",
                "Delivery manifest written.",
                correlation_id=resolved_correlation_id,
                watcher_id=str(job.watcher_id),
                job_id=str(job.job_id),
                attempt_number=attempt_number,
            )

            event_type = None
            if final_state in {"COMPLETED", "COMPLETED_WITH_DELIVERY_ERRORS"}:
                enqueue_event(
                    self.event_repository,
                    stream_name=LIFECYCLE_STREAM_NAME,
                    idempotency_key=_job_completed_idempotency_key(job.job_id, attempt_number),
                    event_payload={
                        "schema_version": "1.0.0",
                        "correlation_id": resolved_correlation_id,
                        "job_id": job.job_id,
                        "watcher_id": job.watcher_id,
                        "attempt_number": attempt_number,
                        "occurred_at": _format_rfc3339(finalized_at),
                        "producer": DELIVERY_SERVICE,
                        "event_type": "job.completed",
                        "payload": {
                            "final_state": final_state,
                            "successful_destination_count": successful_destination_count,
                            "failed_destination_count": failed_destination_count,
                            "completed_at": _format_rfc3339(finalized_at),
                        },
                    },
                )
                self._log(
                    "delivery.job_completed",
                    "Job completed after delivery finalization.",
                    correlation_id=resolved_correlation_id,
                    watcher_id=str(job.watcher_id),
                    job_id=str(job.job_id),
                    attempt_number=attempt_number,
                    state_from="DELIVERING",
                    state_to=final_state,
                )
                event_type = "job.completed"

            return DeliveryWorkerResult(
                job_id=job.job_id,
                status="delivered" if successful_destination_count > 0 else "failed",
                final_state=final_state,
                reason_code=final_reason_code,
                attempt_number=attempt_number,
                event_type=event_type,
                output_manifest_id=final_output_manifest_id,
                successful_destination_count=successful_destination_count,
                failed_destination_count=failed_destination_count,
            )
        finally:
            if claim_id is not None:
                self.stage_claim_repository.release_stage(claim_id, released_at=self.clock())
                self._log(
                    "delivery.claim_released",
                    "Delivery claim released.",
                    correlation_id=resolved_correlation_id,
                    watcher_id=str(job.watcher_id),
                    job_id=str(job.job_id),
                    attempt_number=attempt_number,
                )

    def claim_and_deliver(
        self,
        limit: int = 1,
        correlation_id: str | None = None,
    ) -> DeliveryBatchResult:
        jobs = list(reversed(self.job_repository.list_jobs(state="PROCESSED")))
        retry_ready_jobs = [
            job
            for job in reversed(self.job_repository.list_jobs(state="DELIVERING"))
            if _is_retry_attempt(job.attempt_number)
        ]
        jobs.extend(retry_ready_jobs)
        claimed = 0
        delivered = 0
        failed = 0
        skipped = 0

        for job in jobs[: max(limit, 0)]:
            result = self.deliver_one(job.job_id, correlation_id=correlation_id or str(job.correlation_id))
            if result.status == "delivered":
                claimed += 1
                delivered += 1
            elif result.status == "failed":
                claimed += 1
                failed += 1
            else:
                skipped += 1

        return DeliveryBatchResult(
            claimed=claimed,
            delivered=delivered,
            failed=failed,
            skipped=skipped,
        )

    def _fail_without_delivery_targets(
        self,
        *,
        job,
        attempt_number: int,
        correlation_id: str,
        processed_manifest_row: OutputManifestModel,
        processed_manifest: OutputManifest,
        source_route_tags: tuple[str, ...],
        delivery_start_state: str,
    ) -> DeliveryWorkerResult:
        finalized_at = self.clock()
        self.job_repository.update_state(
            job.job_id,
            new_state="FAILED",
            latest_error_code=REASON_NO_MATCHING_DESTINATION,
            attempt_number=attempt_number,
        )
        self.job_repository.append_state_history(
            job_id=job.job_id,
            previous_state=delivery_start_state,
            new_state="FAILED",
            actor_service=DELIVERY_SERVICE,
            reason_code=REASON_NO_MATCHING_DESTINATION,
            correlation_id=correlation_id,
            transitioned_at=finalized_at,
        )
        final_output_manifest_id = generate_uuid()
        final_manifest = build_output_manifest(
            existing_manifest=processed_manifest,
            destination_outcomes=[],
            status="failed",
            completed_at=_format_rfc3339(finalized_at),
            created_at=_format_rfc3339(finalized_at),
            correlation_id=correlation_id,
            duration_seconds=_manifest_duration_seconds(processed_manifest.started_at, finalized_at),
        )
        self.output_manifest_writer.write_manifest(
            manifest_locator=processed_manifest_row.manifest_locator,
            manifest=final_manifest,
        )
        self.delivery_repository.create_output_manifest(
            output_manifest_id=final_output_manifest_id,
            job_id=job.job_id,
            watcher_id=job.watcher_id,
            schema_version=processed_manifest_row.schema_version,
            manifest_locator=processed_manifest_row.manifest_locator,
            processing_summary_locator=processed_manifest_row.processing_summary_locator,
            produced_output_locators=list(processed_manifest_row.produced_output_locators),
            source_sha256=processed_manifest_row.source_sha256,
            output_sha256=processed_manifest_row.output_sha256,
            destination_outcomes=[],
            finalized_at=finalized_at,
            status="failed",
            correlation_id=correlation_id,
        )
        self._log(
            "delivery.failed",
            "Delivery failed because no destination matched the source route tags.",
            level="WARNING",
            correlation_id=correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            attempt_number=attempt_number,
            state_from=delivery_start_state,
            state_to="FAILED",
            error_code=REASON_NO_MATCHING_DESTINATION,
            route_tags=list(source_route_tags),
        )
        self._log(
            "delivery.manifest_written",
            "Delivery manifest written.",
            correlation_id=correlation_id,
            watcher_id=str(job.watcher_id),
            job_id=str(job.job_id),
            attempt_number=attempt_number,
        )
        return DeliveryWorkerResult(
            job_id=job.job_id,
            status="failed",
            final_state="FAILED",
            reason_code=REASON_NO_MATCHING_DESTINATION,
            attempt_number=attempt_number,
            event_type=None,
            output_manifest_id=final_output_manifest_id,
        )

    def _resolve_targets(
        self,
        watcher_id: UUID | str,
        source_folder_id: UUID | str,
    ) -> tuple[DeliveryRouteResolution, tuple[str, ...]]:
        destinations = [
            row
            for row in self.watcher_repository.list_destinations(watcher_id)
            if bool(getattr(row, "enabled", True))
        ]
        source = next(
            (
                row
                for row in self.watcher_repository.list_sources(watcher_id)
                if str(row.source_folder_id) == str(source_folder_id)
            ),
            None,
        )
        if source is None or not getattr(source, "route_tags", ()):
            return DeliveryRouteResolution(targets=(), unmatched_reason=REASON_NO_MATCHING_DESTINATION), ()
        source_route_tags = tuple(str(tag) for tag in source.route_tags)
        return resolve_delivery_targets(source_route_tags, destinations), source_route_tags

    def _get_latest_processed_manifest(self, job_id: UUID | str) -> OutputManifestModel | None:
        statement = (
            sa.select(OutputManifestModel)
            .where(OutputManifestModel.job_id == UUID(str(job_id)))
            .where(OutputManifestModel.status == "processed")
            .order_by(OutputManifestModel.finalized_at.desc(), OutputManifestModel.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def _load_output_manifest(self, manifest_locator: str) -> OutputManifest | None:
        try:
            local_path = Path(self.filesystem_resolver(manifest_locator))
            payload = json.loads(local_path.read_text(encoding="utf-8"))
            return OutputManifest.model_validate(payload)
        except (OSError, ValidationError, ValueError, json.JSONDecodeError):
            return None


    def _record_transfer_health_failure(
        self,
        *,
        job,
        destination_folder_id: UUID | str,
        reason_code: str,
    ) -> None:
        if reason_code == SOURCE_TRANSFER_FAILED:
            self.watcher_repository.update_source_health(
                job.source_folder_id,
                health_status="red",
                reason_code=reason_code,
            )
            return
        self.watcher_repository.update_destination_health(
            destination_folder_id,
            health_status="red",
            reason_code=reason_code,
        )

    def _final_state_from_outcomes(
        self,
        *,
        destination_outcomes: list[dict[str, object]],
        attempt_number: int,
    ) -> tuple[str, str, str]:
        delivered_outcomes = [outcome for outcome in destination_outcomes if outcome["status"] == "delivered"]
        failed_outcomes = [outcome for outcome in destination_outcomes if outcome["status"] == "failed"]

        if delivered_outcomes and not failed_outcomes:
            return "COMPLETED", "delivered", REASON_DELIVERY_COMPLETED
        if delivered_outcomes and failed_outcomes:
            reason_code = str(failed_outcomes[0].get("reason_code") or "DELIVERY_FAILED")
            return "COMPLETED_WITH_DELIVERY_ERRORS", "completed_with_delivery_errors", reason_code

        all_retryable = bool(failed_outcomes) and all(bool(outcome.get("retryable")) for outcome in failed_outcomes)
        if all_retryable and attempt_number < self.retry_max_attempts:
            reason_code = str(failed_outcomes[0].get("reason_code") or "DELIVERY_FAILED")
            return "RETRY_PENDING", "failed", reason_code

        reason_code = str(failed_outcomes[0].get("reason_code") or "DELIVERY_FAILED")
        return "FAILED", "failed", reason_code

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
            service=DELIVERY_SERVICE,
            component="delivery.worker",
            event=event,
            message=message,
            level=level,
            correlation_id=correlation_id,
            allowed_container_roots=self.path_policy.source_roots + self.path_policy.destination_roots,
            **fields,
        )
        self.log_records.append(record)

    @staticmethod
    def _resolve_attempt_number(value: int | None) -> int:
        if value is None or value < 1:
            return 1
        return int(value)


def _build_finalized_locator(
    *,
    destination_root_locator: str,
    watcher_id: UUID | str,
    job_id: UUID | str,
    as_of_date,
    source_output_locator: str,
) -> str:
    suffix = PurePosixPath(source_output_locator).suffix
    file_name = "output" if not suffix else f"output{suffix}"
    normalized_root = destination_root_locator.rstrip("/")
    return (
        f"{normalized_root}/watcher_id={watcher_id}/date={as_of_date.isoformat()}/"
        f"job_id={job_id}/{file_name}"
    )


def _build_temporary_locator(finalized_locator: str) -> str:
    finalized_path = PurePosixPath(finalized_locator)
    parent = finalized_path.parent.as_posix().rstrip("/")
    return f"{parent}/.{finalized_path.name}.tmp"


def _is_retry_attempt(attempt_number: int | None) -> bool:
    return attempt_number is not None and attempt_number > 1


def _is_deliverable_state(state: str, attempt_number: int | None) -> bool:
    return state == "PROCESSED" or (state == "DELIVERING" and _is_retry_attempt(attempt_number))


def _delivery_idempotency_key(
    event_type: str,
    job_id: UUID | str,
    destination_folder_id: UUID | str,
    attempt_number: int,
) -> str:
    return f"{event_type}:{job_id}:{destination_folder_id}:{attempt_number}"


def _job_completed_idempotency_key(job_id: UUID | str, attempt_number: int) -> str:
    return f"job.completed:{job_id}:job:{attempt_number}"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_rfc3339(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _duration_seconds(started_at: datetime, completed_at: datetime) -> float:
    delta = (_as_utc(completed_at) - _as_utc(started_at)).total_seconds()
    return max(0.0, float(delta))


def _manifest_duration_seconds(started_at: str, finalized_at: datetime) -> int:
    try:
        started_at_datetime = _parse_rfc3339_utc(started_at)
    except ValueError:
        return 0
    return max(0, int(round(_duration_seconds(started_at_datetime, finalized_at))))


__all__ = [
    "DeliveryBatchResult",
    "DeliveryWorker",
    "DeliveryWorkerResult",
]
