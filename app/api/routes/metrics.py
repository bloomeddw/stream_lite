"""Dashboard summary metrics routes."""

from __future__ import annotations

from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session, get_or_create_correlation_id
from app.api.errors import ApiError
from app.api.schemas.api_models import MetricsSummaryResponse
from app.db.models import (
    DeliveryAttemptModel,
    EventOutboxModel,
    JobModel,
    ProcessingAttemptModel,
    RetryScheduleModel,
    ValidationAttemptModel,
    WatcherModel,
)

router = APIRouter()


@router.get("/metrics/summary", response_model=MetricsSummaryResponse)
def get_metrics_summary(
    session: Annotated[Session, Depends(get_db_session)],
    correlation_id: Annotated[str, Depends(get_or_create_correlation_id)],
) -> MetricsSummaryResponse:
    try:
        return MetricsSummaryResponse(
            job_counts=_count_by(session, JobModel.state),
            stage_durations_seconds={
                "validation_avg": _average(session, ValidationAttemptModel.duration_seconds),
                "processing_avg": _average(session, ProcessingAttemptModel.duration_seconds),
                "delivery_avg": _average(session, DeliveryAttemptModel.completed_at),
            },
            queue_lag=_queue_lag(session),
            retry_counts=_count_by(session, RetryScheduleModel.status),
            delivery_counts=_count_by(session, DeliveryAttemptModel.status),
            watcher_counts=_count_by(session, WatcherModel.lifecycle_state),
            correlation_id=correlation_id,
        )
    except Exception as exc:
        raise ApiError(
            503,
            error_code="METRICS_UNAVAILABLE",
            message="Metrics summary is unavailable.",
            correlation_id=correlation_id,
        ) from exc


def _count_by(session: Session, column) -> dict[str, int]:  # type: ignore[no-untyped-def]
    rows = session.execute(
        sa.select(column, sa.func.count()).group_by(column),
    ).all()
    return {str(key): int(count) for key, count in rows if key is not None}


def _average(session: Session, column) -> float:  # type: ignore[no-untyped-def]
    if column is DeliveryAttemptModel.completed_at:
        return 0.0
    value = session.scalar(sa.select(sa.func.avg(column)))
    return round(float(value or 0.0), 6)


def _queue_lag(session: Session) -> dict[str, int]:
    rows = session.execute(
        sa.select(EventOutboxModel.stream_name, sa.func.count())
        .where(EventOutboxModel.status.in_(("pending", "publish_failed")))
        .group_by(EventOutboxModel.stream_name),
    ).all()
    return {str(key): int(count) for key, count in rows if key is not None}


__all__ = ["router"]
