"""Retry schedule persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import RetryScheduleModel

from .base import RepositoryBase


class RetryRepository(RepositoryBase):
    def get_retry_schedule(self, retry_schedule_id: UUID | str) -> RetryScheduleModel | None:
        return self.session.get(RetryScheduleModel, self._ensure_uuid(retry_schedule_id))

    def schedule_retry(
        self,
        *,
        retry_schedule_id: UUID | str | None = None,
        job_id: UUID | str,
        failed_stage: str,
        failure_class: str,
        due_at: datetime,
        backoff_seconds: float,
        attempt_number: int,
        max_attempts: int,
        jitter_enabled: bool,
        next_stage: str,
        correlation_id: UUID | str,
        status: str = "scheduled",
        last_error_code: str | None = None,
    ) -> RetryScheduleModel:
        record = RetryScheduleModel(
            retry_schedule_id=self._ensure_uuid(retry_schedule_id),
            job_id=self._ensure_uuid(job_id),
            failed_stage=failed_stage,
            failure_class=failure_class,
            due_at=due_at,
            backoff_seconds=backoff_seconds,
            attempt_number=attempt_number,
            max_attempts=max_attempts,
            jitter_enabled=jitter_enabled,
            status=status,
            next_stage=next_stage,
            last_error_code=last_error_code,
            correlation_id=self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def claim_due_retries(self, *, as_of: datetime | None = None, limit: int = 100) -> list[RetryScheduleModel]:
        boundary = as_of or self._now()
        statement = (
            sa.select(RetryScheduleModel)
            .where(RetryScheduleModel.status == "scheduled")
            .where(RetryScheduleModel.due_at <= boundary)
            .order_by(RetryScheduleModel.due_at.asc(), RetryScheduleModel.retry_schedule_id.asc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def mark_retry_attempted(self, retry_schedule_id: UUID | str) -> RetryScheduleModel:
        record = self.get_retry_schedule(retry_schedule_id)
        if record is None:
            raise ValueError("retry schedule not found")
        record.status = "attempted"
        record.updated_at = self._now()
        self.session.flush()
        return record

    def mark_retry_exhausted(self, retry_schedule_id: UUID | str, *, last_error_code: str | None = None) -> RetryScheduleModel:
        record = self.get_retry_schedule(retry_schedule_id)
        if record is None:
            raise ValueError("retry schedule not found")
        record.status = "exhausted"
        record.last_error_code = last_error_code
        record.updated_at = self._now()
        self.session.flush()
        return record

    def mark_retry_failed(
        self,
        retry_schedule_id: UUID | str,
        *,
        last_error_code: str | None = None,
    ) -> RetryScheduleModel:
        record = self.get_retry_schedule(retry_schedule_id)
        if record is None:
            raise ValueError("retry schedule not found")
        record.status = "failed"
        record.last_error_code = last_error_code
        record.updated_at = self._now()
        self.session.flush()
        return record


__all__ = ["RetryRepository"]
