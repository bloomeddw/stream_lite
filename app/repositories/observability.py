"""Operational summary and health-observation persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import HealthObservationModel, OperationalLogSummaryModel

from .base import RepositoryBase


class OperationalLogRepository(RepositoryBase):
    def write_summary(
        self,
        *,
        log_summary_id: UUID | str | None = None,
        event_name: str,
        sanitized_message: str,
        job_id: UUID | str | None = None,
        watcher_id: UUID | str | None = None,
        error_code: str | None = None,
        correlation_id: UUID | str | None = None,
    ) -> OperationalLogSummaryModel:
        record = OperationalLogSummaryModel(
            log_summary_id=self._ensure_uuid(log_summary_id),
            job_id=None if job_id is None else self._ensure_uuid(job_id),
            watcher_id=None if watcher_id is None else self._ensure_uuid(watcher_id),
            event_name=event_name,
            error_code=error_code,
            sanitized_message=sanitized_message,
            correlation_id=None if correlation_id is None else self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_summaries(
        self,
        *,
        limit: int = 100,
        job_id: UUID | str | None = None,
        watcher_id: UUID | str | None = None,
    ) -> list[OperationalLogSummaryModel]:
        statement = sa.select(OperationalLogSummaryModel)
        if job_id is not None:
            statement = statement.where(OperationalLogSummaryModel.job_id == self._ensure_uuid(job_id))
        if watcher_id is not None:
            statement = statement.where(OperationalLogSummaryModel.watcher_id == self._ensure_uuid(watcher_id))
        statement = statement.order_by(OperationalLogSummaryModel.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement))


class HealthRepository(RepositoryBase):
    def write_observation(
        self,
        *,
        health_observation_id: UUID | str | None = None,
        status: str,
        checked_at: datetime,
        watcher_id: UUID | str | None = None,
        folder_id: UUID | str | None = None,
        folder_role: str | None = None,
        dependency_name: str | None = None,
        reason_code: str | None = None,
        correlation_id: UUID | str | None = None,
    ) -> HealthObservationModel:
        record = HealthObservationModel(
            health_observation_id=self._ensure_uuid(health_observation_id),
            watcher_id=None if watcher_id is None else self._ensure_uuid(watcher_id),
            folder_id=None if folder_id is None else self._ensure_uuid(folder_id),
            folder_role=folder_role,
            dependency_name=dependency_name,
            status=status,
            reason_code=reason_code,
            checked_at=checked_at,
            correlation_id=None if correlation_id is None else self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_latest_observations(
        self,
        *,
        limit: int = 100,
        watcher_id: UUID | str | None = None,
    ) -> list[HealthObservationModel]:
        statement = sa.select(HealthObservationModel)
        if watcher_id is not None:
            statement = statement.where(HealthObservationModel.watcher_id == self._ensure_uuid(watcher_id))
        statement = statement.order_by(HealthObservationModel.checked_at.desc()).limit(limit)
        return list(self.session.scalars(statement))


__all__ = ["HealthRepository", "OperationalLogRepository"]
