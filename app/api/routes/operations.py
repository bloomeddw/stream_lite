"""Operational log summary routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    PaginationParams,
    get_operational_log_repository,
    get_or_create_correlation_id,
    get_pagination,
)
from app.api.errors import ApiError
from app.api.schemas.api_models import OperationalLogItem, OperationalLogListResponse
from app.repositories.observability import OperationalLogRepository

router = APIRouter()


@router.get("/logs", response_model=OperationalLogListResponse)
def list_logs(
    watcher_id: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
    pagination: Annotated[PaginationParams, Depends(get_pagination)] = PaginationParams(),
    repository: Annotated[OperationalLogRepository, Depends(get_operational_log_repository)] = None,  # type: ignore[assignment]
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)] = "",
) -> OperationalLogListResponse:
    parsed_watcher_id = _parse_uuid_filter("watcher_id", watcher_id, correlation_id)
    parsed_job_id = _parse_uuid_filter("job_id", job_id, correlation_id)
    records = repository.list_summaries(
        limit=500,
        job_id=parsed_job_id,
        watcher_id=parsed_watcher_id,
    )
    ordered = sorted(records, key=lambda row: (-row.created_at.timestamp(), str(row.log_summary_id)))
    page = ordered[pagination.offset : pagination.offset + pagination.limit]
    items = [
        OperationalLogItem(
            timestamp=_format_datetime(row.created_at),
            level="INFO",
            service="api",
            component="operations",
            event=row.event_name,
            correlation_id=row.correlation_id,
            job_id=row.job_id,
            file_id=None,
            message=_sanitize_message(row.sanitized_message),
            error_code=row.error_code,
            duration_ms=None,
        )
        for row in page
    ]
    return OperationalLogListResponse(
        items=items,
        limit=pagination.limit,
        offset=pagination.offset,
        total=len(ordered),
        correlation_id=correlation_id,
    )


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


def _sanitize_message(message: str) -> str:
    if ":\\" in message or message.lower().startswith("file://"):
        return "[redacted-host-path]"
    return message


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["router"]
