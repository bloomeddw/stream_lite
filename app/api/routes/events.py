"""Persisted event summary routes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app._schema_types import EVENT_TYPE_PATTERN
from app.api.dependencies import (
    PaginationParams,
    get_event_outbox_repository,
    get_or_create_correlation_id,
    get_pagination,
)
from app.api.errors import ApiError
from app.api.schemas.api_models import EventListResponse
from app.events.outbox import list_event_summaries
from app.repositories.events import EventOutboxRepository

router = APIRouter()


@router.get("/events", response_model=EventListResponse)
def list_events(
    watcher_id: str | None = Query(default=None),
    job_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    from_occurred_at: str | None = Query(default=None),
    to_occurred_at: str | None = Query(default=None),
    pagination: Annotated[PaginationParams, Depends(get_pagination)] = PaginationParams(),
    repository: Annotated[EventOutboxRepository, Depends(get_event_outbox_repository)] = None,  # type: ignore[assignment]
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)] = "",
) -> EventListResponse:
    parsed_watcher_id = _parse_uuid_filter("watcher_id", watcher_id, correlation_id)
    parsed_job_id = _parse_uuid_filter("job_id", job_id, correlation_id)
    parsed_event_type = _parse_event_type(event_type, correlation_id)
    parsed_from = _parse_datetime_filter("from_occurred_at", from_occurred_at, correlation_id)
    parsed_to = _parse_datetime_filter("to_occurred_at", to_occurred_at, correlation_id)
    if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
        raise ApiError(
            422,
            error_code="FILTER_INVALID",
            message="from_occurred_at must be less than or equal to to_occurred_at.",
            field="from_occurred_at",
            correlation_id=correlation_id,
        )

    items, total = list_event_summaries(
        repository,
        watcher_id=parsed_watcher_id,
        job_id=parsed_job_id,
        event_type=parsed_event_type,
        from_occurred_at=parsed_from,
        to_occurred_at=parsed_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return EventListResponse(
        items=items,
        limit=pagination.limit,
        offset=pagination.offset,
        total=total,
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


def _parse_event_type(value: str | None, correlation_id: str) -> str | None:
    if value is None:
        return None
    if not EVENT_TYPE_PATTERN.fullmatch(value):
        raise ApiError(
            422,
            error_code="FILTER_INVALID",
            message="event_type must match the documented event name pattern.",
            field="event_type",
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


__all__ = ["router"]
