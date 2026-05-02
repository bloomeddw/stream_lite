"""Job inspection and manual retry command routes."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app import generate_uuid, generate_uuid_str
from app.api.dependencies import (
    PaginationParams,
    get_command_repository,
    get_delivery_repository,
    get_idempotency_key,
    get_job_repository,
    get_operational_log_repository,
    get_or_create_correlation_id,
    get_pagination,
    get_processing_repository,
    get_retry_repository,
    get_settings,
    get_validation_repository,
    get_watcher_repository,
)
from app.api.errors import ApiError
from app.api.schemas.api_models import (
    CommandAcceptedResponse,
    JobAttemptSummary,
    JobDestinationSummary,
    JobDetailResponse,
    JobHistoryEntry,
    JobHistoryResponse,
    JobListItem,
    JobListResponse,
    JobSource,
    RetryCommandRequest,
)
from app.config.settings import StreamLiteSettings
from app.db.models import (
    DeliveryAttemptModel,
    JobModel,
    ProcessingAttemptModel,
    RetryScheduleModel,
    ValidationAttemptModel,
)
from app.repositories.commands import CommandRepository
from app.repositories.delivery import DeliveryRepository
from app.repositories.jobs import JobRepository
from app.repositories.observability import OperationalLogRepository
from app.repositories.processing import ProcessingRepository
from app.repositories.retry import RetryRepository
from app.repositories.validation import ValidationRepository
from app.repositories.watchers import WatcherRepository

router = APIRouter(prefix="/jobs")

_JOB_STATES = {
    "DETECTED",
    "STABILIZING",
    "REGISTERED",
    "VALIDATING",
    "VALIDATED",
    "INVALID",
    "QUARANTINED",
    "PROCESSING",
    "PROCESSED",
    "DELIVERING",
    "DELIVERED",
    "RETRY_PENDING",
    "FAILED",
    "COMPLETED",
    "COMPLETED_WITH_DELIVERY_ERRORS",
}
_TERMINAL_STATES = {
    "FAILED",
    "COMPLETED",
    "COMPLETED_WITH_DELIVERY_ERRORS",
    "QUARANTINED",
}
_NON_RETRYABLE_CODES = {
    "EXTENSION_NOT_ALLOWED",
    "FILE_EMPTY",
    "FILE_TOO_LARGE",
    "PATH_POLICY_VIOLATION",
    "SCHEMA_INVALID",
}


@router.get("", response_model=JobListResponse)
def list_jobs(
    watcher_id: str | None = Query(default=None),
    state: str | None = Query(default=None),
    terminal: str | None = Query(default=None),
    file_name: str | None = Query(default=None),
    created_from: str | None = Query(default=None),
    created_to: str | None = Query(default=None),
    pagination: Annotated[PaginationParams, Depends(get_pagination)] = PaginationParams(),
    repository: Annotated[JobRepository, Depends(get_job_repository)] = None,  # type: ignore[assignment]
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)] = "",
) -> JobListResponse:
    parsed_watcher_id = _parse_uuid_filter("watcher_id", watcher_id, correlation_id)
    parsed_state = _parse_job_state("state", state, correlation_id)
    parsed_terminal = _parse_job_state("terminal", terminal, correlation_id, terminal_only=True)
    parsed_from = _parse_datetime_filter("created_from", created_from, correlation_id)
    parsed_to = _parse_datetime_filter("created_to", created_to, correlation_id)
    if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
        raise ApiError(
            422,
            error_code="FILTER_INVALID",
            message="created_from must be less than or equal to created_to.",
            field="created_from",
            correlation_id=correlation_id,
        )

    jobs = repository.list_jobs(
        watcher_id=parsed_watcher_id,
        state=parsed_state,
        terminal_state=parsed_terminal,
        file_name=file_name,
        created_after=parsed_from,
        created_before=parsed_to,
    )
    ordered = sorted(jobs, key=lambda row: (-row.created_at.timestamp(), str(row.job_id)))
    page = ordered[pagination.offset : pagination.offset + pagination.limit]
    items = [
        JobListItem(
            job_id=row.job_id,
            watcher_id=row.watcher_id,
            state=row.state,
            source_display_path=row.source_display_path,
            created_at=_format_datetime(row.created_at),
            updated_at=_format_datetime(row.updated_at),
            latest_error_code=row.latest_error_code,
        )
        for row in page
    ]
    return JobListResponse(
        items=items,
        limit=pagination.limit,
        offset=pagination.offset,
        total=len(ordered),
        correlation_id=correlation_id,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job_detail(
    job_id: UUID,
    repository: Annotated[JobRepository, Depends(get_job_repository)],
    watcher_repository: Annotated[WatcherRepository, Depends(get_watcher_repository)],
    validation_repository: Annotated[ValidationRepository, Depends(get_validation_repository)],
    processing_repository: Annotated[ProcessingRepository, Depends(get_processing_repository)],
    delivery_repository: Annotated[DeliveryRepository, Depends(get_delivery_repository)],
    retry_repository: Annotated[RetryRepository, Depends(get_retry_repository)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> JobDetailResponse:
    job = repository.get_job(job_id)
    if job is None:
        raise ApiError(
            404,
            error_code="JOB_NOT_FOUND",
            message=f"Job {job_id} was not found.",
            resource_id=str(job_id),
            correlation_id=correlation_id,
        )

    session = repository.session
    destinations = _build_destination_summaries(session, watcher_repository, job)
    attempt_summary = JobAttemptSummary(
        validation_attempts=_count_records(session, ValidationAttemptModel, job.job_id),
        processing_attempts=_count_records(session, ProcessingAttemptModel, job.job_id),
        delivery_attempts=_count_records(session, DeliveryAttemptModel, job.job_id),
        retry_attempts=_count_records(session, RetryScheduleModel, job.job_id),
        last_attempt_at=_last_attempt_at(session, job.job_id),
    )
    latest_error = None
    if job.latest_error_code is not None:
        latest_error = {
            "error_code": job.latest_error_code,
            "message": f"Latest job error: {job.latest_error_code}.",
            "field": None,
            "resource_id": str(job.job_id),
            "current_state": job.state,
            "correlation_id": correlation_id,
        }

    return JobDetailResponse(
        job_id=job.job_id,
        watcher_id=job.watcher_id,
        state=job.state,
        source=JobSource(
            file_id=job.file_id,
            display_path=job.source_display_path,
            source_folder_id=job.source_folder_id,
            size_bytes=job.source_size_bytes,
            sha256=job.source_sha256 or ("0" * 64),
        ),
        destinations=destinations,
        attempt_summary=attempt_summary,
        latest_error=latest_error,
        created_at=_format_datetime(job.created_at),
        updated_at=_format_datetime(job.updated_at),
        correlation_id=correlation_id,
    )


@router.get("/{job_id}/history", response_model=JobHistoryResponse)
def get_job_history(
    job_id: UUID,
    repository: Annotated[JobRepository, Depends(get_job_repository)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> JobHistoryResponse:
    if repository.get_job(job_id) is None:
        raise ApiError(
            404,
            error_code="JOB_NOT_FOUND",
            message=f"Job {job_id} was not found.",
            resource_id=str(job_id),
            correlation_id=correlation_id,
        )
    rows = repository.list_state_history(job_id)
    return JobHistoryResponse(
        job_id=job_id,
        history=[
            JobHistoryEntry(
                from_state=row.previous_state,
                to_state=row.new_state,
                actor_service=row.actor_service,
                reason_code=row.reason_code,
                occurred_at=_format_datetime(row.transitioned_at),
                event_id=row.event_id or row.history_id,
            )
            for row in rows
        ],
        correlation_id=correlation_id,
    )


@router.post("/{job_id}/retry", response_model=CommandAcceptedResponse, status_code=202)
def request_retry(
    job_id: UUID,
    payload: RetryCommandRequest,
    repository: Annotated[JobRepository, Depends(get_job_repository)],
    command_repository: Annotated[CommandRepository, Depends(get_command_repository)],
    log_repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)],
    settings: Annotated[StreamLiteSettings, Depends(get_settings)],
    idempotency_key: Annotated[str | None, Depends(get_idempotency_key)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
):
    resolved_correlation_id = str(payload.correlation_id or correlation_id)
    if payload.reason is None or not payload.reason.strip():
        raise ApiError(
            422,
            error_code="REQUEST_VALIDATION_FAILED",
            message="reason is required for manual retry commands.",
            field="reason",
            correlation_id=resolved_correlation_id,
        )

    scope = f"job.retry:{job_id}"
    payload_hash = _payload_hash(payload.model_dump(mode="json", exclude={"correlation_id": True}))
    if idempotency_key is not None:
        existing_record = command_repository.get_key(scope=scope, idempotency_key=idempotency_key)
        if existing_record is not None:
            if existing_record.payload_hash is not None and existing_record.payload_hash != payload_hash:
                raise ApiError(
                    409,
                    error_code="IDEMPOTENCY_KEY_CONFLICT",
                    message="Idempotency-Key was already used with a different request payload.",
                    resource_id=str(job_id),
                    correlation_id=resolved_correlation_id,
                )
            if existing_record.first_response_json is not None:
                response = CommandAcceptedResponse.model_validate(existing_record.first_response_json)
                return JSONResponse(status_code=202, content=response.model_dump(mode="json"))

    job = repository.get_job(job_id)
    if job is None:
        raise ApiError(
            404,
            error_code="JOB_NOT_FOUND",
            message=f"Job {job_id} was not found.",
            resource_id=str(job_id),
            correlation_id=resolved_correlation_id,
        )
    if job.state != "FAILED":
        raise ApiError(
            409,
            error_code="JOB_NOT_RETRYABLE",
            message="Only FAILED jobs are retryable.",
            resource_id=str(job_id),
            current_state=job.state,
            correlation_id=resolved_correlation_id,
        )
    if job.latest_error_code in _NON_RETRYABLE_CODES:
        raise ApiError(
            409,
            error_code="JOB_NOT_RETRYABLE",
            message="The latest failure code is not retryable.",
            resource_id=str(job_id),
            current_state=job.state,
            correlation_id=resolved_correlation_id,
        )
    if _retry_exhausted(repository.session, job.job_id, settings.retry_max_attempts):
        raise ApiError(
            409,
            error_code="RETRY_LIMIT_EXHAUSTED",
            message="Retry attempts are exhausted for this job.",
            resource_id=str(job_id),
            current_state=job.state,
            correlation_id=resolved_correlation_id,
        )
    if _latest_retry_stage(repository.session, job.job_id) is None:
        raise ApiError(
            409,
            error_code="JOB_NOT_RETRYABLE",
            message="The latest failed stage is not retryable.",
            resource_id=str(job_id),
            current_state=job.state,
            correlation_id=resolved_correlation_id,
        )

    created = command_repository.create_command(
        command_id=generate_uuid(),
        command_type="job.retry",
        target_resource_type="job",
        target_resource_id=job_id,
        requested_by=payload.requested_by,
        operator_reason=payload.reason.strip(),
        idempotency_key=idempotency_key or generate_uuid_str(),
        correlation_id=resolved_correlation_id,
    )
    response = CommandAcceptedResponse(
        command_id=created.command_id,
        status="accepted",
        target_resource_type="job",
        target_resource_id=job_id,
        accepted_at=_format_datetime(created.created_at),
        correlation_id=resolved_correlation_id,
    )
    if idempotency_key is not None:
        command_repository.reserve_idempotency_key(
            idempotency_key_id=generate_uuid(),
            scope=scope,
            idempotency_key=idempotency_key,
            target_type="job",
            target_id=job_id,
            payload_hash=payload_hash,
            first_response_json=response.model_dump(mode="json"),
        )
    log_repository.write_summary(
        event_name="job.retry_requested",
        sanitized_message=f"Retry requested for job {job_id}.",
        job_id=job_id,
        watcher_id=job.watcher_id,
        correlation_id=resolved_correlation_id,
    )
    repository.session.commit()
    return JSONResponse(status_code=202, content=response.model_dump(mode="json"))


def _build_destination_summaries(
    session,
    watcher_repository: WatcherRepository,
    job: JobModel,
) -> list[JobDestinationSummary]:
    route_matches = watcher_repository.list_route_matches(job.watcher_id)
    matched_destinations_by_source: dict[UUID, dict[UUID, list[str]]] = {}
    for row in route_matches:
        if row.destination_folder_id is None:
            continue
        matched_destinations_by_source.setdefault(row.source_folder_id, {})[row.destination_folder_id] = list(
            row.matched_route_tags,
        )
    destination_map = matched_destinations_by_source.get(job.source_folder_id, {})
    watcher_destinations = {
        row.destination_folder_id: row
        for row in watcher_repository.list_destinations(job.watcher_id)
    }
    delivery_attempts = session.scalars(
        sa.select(DeliveryAttemptModel)
        .where(DeliveryAttemptModel.job_id == job.job_id)
        .order_by(
            DeliveryAttemptModel.attempt_number.desc(),
            DeliveryAttemptModel.created_at.desc(),
        ),
    ).all()
    latest_attempt_by_destination: dict[UUID, DeliveryAttemptModel] = {}
    for attempt in delivery_attempts:
        latest_attempt_by_destination.setdefault(attempt.destination_folder_id, attempt)

    destination_ids = sorted(destination_map, key=str)
    if not destination_ids:
        destination_ids = sorted(watcher_destinations, key=str)

    summaries: list[JobDestinationSummary] = []
    for destination_id in destination_ids:
        destination = watcher_destinations.get(destination_id)
        if destination is None:
            continue
        latest_attempt = latest_attempt_by_destination.get(destination_id)
        status = "pending"
        reason_code = destination.reason_code
        matched_tags = destination_map.get(destination_id, destination.route_tags)
        if latest_attempt is not None:
            if latest_attempt.status == "failed":
                status = "failed"
                reason_code = latest_attempt.failure_code
            elif latest_attempt.status == "delivered":
                status = "delivered"
                reason_code = None
            else:
                status = "pending"
        summaries.append(
            JobDestinationSummary(
                destination_folder_id=destination.destination_folder_id,
                display_path=destination.display_path,
                route_tags=destination.route_tags,
                matched_tags=matched_tags,
                status=status,
                reason_code=reason_code,
            )
        )
    return summaries


def _count_records(session, model, job_id: UUID) -> int:  # type: ignore[no-untyped-def]
    count = session.scalar(
        sa.select(sa.func.count()).select_from(model).where(model.job_id == job_id),
    )
    return int(count or 0)


def _last_attempt_at(session, job_id: UUID) -> str | None:  # type: ignore[no-untyped-def]
    timestamps = [
        session.scalar(
            sa.select(sa.func.max(ValidationAttemptModel.started_at)).where(ValidationAttemptModel.job_id == job_id),
        ),
        session.scalar(
            sa.select(sa.func.max(ProcessingAttemptModel.started_at)).where(ProcessingAttemptModel.job_id == job_id),
        ),
        session.scalar(
            sa.select(sa.func.max(DeliveryAttemptModel.started_at)).where(DeliveryAttemptModel.job_id == job_id),
        ),
        session.scalar(
            sa.select(sa.func.max(RetryScheduleModel.created_at)).where(RetryScheduleModel.job_id == job_id),
        ),
    ]
    values = [timestamp for timestamp in timestamps if timestamp is not None]
    if not values:
        return None
    return _format_datetime(max(values))


def _retry_exhausted(session, job_id: UUID, retry_max_attempts: int) -> bool:  # type: ignore[no-untyped-def]
    latest_retry = session.scalar(
        sa.select(RetryScheduleModel)
        .where(RetryScheduleModel.job_id == job_id)
        .order_by(RetryScheduleModel.attempt_number.desc(), RetryScheduleModel.created_at.desc())
        .limit(1),
    )
    if latest_retry is None:
        return False
    return latest_retry.status == "exhausted" or latest_retry.attempt_number >= retry_max_attempts


def _latest_retry_stage(session, job_id: UUID) -> str | None:  # type: ignore[no-untyped-def]
    latest_delivery_failure = session.scalar(
        sa.select(DeliveryAttemptModel)
        .where(DeliveryAttemptModel.job_id == job_id, DeliveryAttemptModel.status == "failed")
        .order_by(DeliveryAttemptModel.completed_at.desc().nullslast(), DeliveryAttemptModel.created_at.desc())
        .limit(1),
    )
    latest_processing_failure = session.scalar(
        sa.select(ProcessingAttemptModel)
        .where(ProcessingAttemptModel.job_id == job_id, ProcessingAttemptModel.status == "failed")
        .order_by(ProcessingAttemptModel.completed_at.desc().nullslast(), ProcessingAttemptModel.created_at.desc())
        .limit(1),
    )
    if latest_delivery_failure is None and latest_processing_failure is None:
        return None
    delivery_time = (
        latest_delivery_failure.completed_at or latest_delivery_failure.created_at
        if latest_delivery_failure is not None
        else None
    )
    processing_time = (
        latest_processing_failure.completed_at or latest_processing_failure.created_at
        if latest_processing_failure is not None
        else None
    )
    if delivery_time is not None and (processing_time is None or delivery_time >= processing_time):
        return "delivery"
    return "processing"


def _parse_uuid_filter(field: str, value: str | None, correlation_id: str) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError as exc:
        raise ApiError(
            422,
            error_code="FILTER_INVALID",
            message=f"{field} must be a valid UUID.",
            field=field,
            correlation_id=correlation_id,
        ) from exc


def _parse_job_state(
    field: str,
    value: str | None,
    correlation_id: str,
    *,
    terminal_only: bool = False,
) -> str | None:
    if value is None:
        return None
    allowed = _TERMINAL_STATES if terminal_only else _JOB_STATES
    if value not in allowed:
        raise ApiError(
            422,
            error_code="FILTER_INVALID",
            message=f"{field} must be one of {', '.join(sorted(allowed))}.",
            field=field,
            correlation_id=correlation_id,
        )
    return value


def _parse_datetime_filter(field: str, value: str | None, correlation_id: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApiError(
            422,
            error_code="FILTER_INVALID",
            message=f"{field} must be an RFC 3339 UTC timestamp.",
            field=field,
            correlation_id=correlation_id,
        ) from exc
    if parsed.tzinfo is None:
        raise ApiError(
            422,
            error_code="FILTER_INVALID",
            message=f"{field} must be an RFC 3339 UTC timestamp.",
            field=field,
            correlation_id=correlation_id,
        )
    return parsed


def _payload_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["router"]
