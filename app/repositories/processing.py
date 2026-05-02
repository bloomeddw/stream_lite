"""Processing attempt persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.db.models import ProcessingAttemptModel

from .base import RepositoryBase


class ProcessingRepository(RepositoryBase):
    def create_processing_attempt(
        self,
        *,
        processing_attempt_id: UUID | str | None = None,
        job_id: UUID | str,
        attempt_number: int,
        engine: str,
        engine_version: str,
        input_locator: str,
        started_at: datetime,
        correlation_id: UUID | str,
        status: str = "started",
    ) -> ProcessingAttemptModel:
        record = ProcessingAttemptModel(
            processing_attempt_id=self._ensure_uuid(processing_attempt_id),
            job_id=self._ensure_uuid(job_id),
            attempt_number=attempt_number,
            engine=engine,
            engine_version=engine_version,
            input_locator=input_locator,
            started_at=started_at,
            status=status,
            correlation_id=self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def complete_processing_attempt(
        self,
        processing_attempt_id: UUID | str,
        *,
        output_locator: str,
        summary_locator: str,
        completed_at: datetime,
        duration_seconds: float,
        row_count: int | None = None,
        record_count: int | None = None,
        byte_count: int | None = None,
    ) -> ProcessingAttemptModel:
        record = self.session.get(ProcessingAttemptModel, self._ensure_uuid(processing_attempt_id))
        if record is None:
            raise ValueError("processing attempt not found")
        record.output_locator = output_locator
        record.summary_locator = summary_locator
        record.completed_at = completed_at
        record.duration_seconds = duration_seconds
        record.row_count = row_count
        record.record_count = record_count
        record.byte_count = byte_count
        record.status = "processed"
        record.updated_at = self._now()
        self.session.flush()
        return record

    def fail_processing_attempt(
        self,
        processing_attempt_id: UUID | str,
        *,
        error_code: str,
        completed_at: datetime,
        duration_seconds: float,
    ) -> ProcessingAttemptModel:
        record = self.session.get(ProcessingAttemptModel, self._ensure_uuid(processing_attempt_id))
        if record is None:
            raise ValueError("processing attempt not found")
        record.error_code = error_code
        record.completed_at = completed_at
        record.duration_seconds = duration_seconds
        record.status = "failed"
        record.updated_at = self._now()
        self.session.flush()
        return record


__all__ = ["ProcessingRepository"]
