"""Validation and quarantine persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import QuarantineRecordModel, ValidationAttemptModel

from .base import RepositoryBase


class ValidationRepository(RepositoryBase):
    def create_validation_attempt(
        self,
        *,
        validation_attempt_id: UUID | str | None = None,
        job_id: UUID | str,
        attempt_number: int,
        validation_status: str,
        rules_applied: list[str],
        reason_codes: list[str],
        started_at: datetime,
        correlation_id: UUID | str,
        completed_at: datetime | None = None,
        duration_seconds: float | None = None,
    ) -> ValidationAttemptModel:
        record = ValidationAttemptModel(
            validation_attempt_id=self._ensure_uuid(validation_attempt_id),
            job_id=self._ensure_uuid(job_id),
            attempt_number=attempt_number,
            validation_status=validation_status,
            rules_applied=rules_applied,
            reason_codes=reason_codes,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            correlation_id=self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_latest_attempt(self, job_id: UUID | str) -> ValidationAttemptModel | None:
        statement = (
            sa.select(ValidationAttemptModel)
            .where(ValidationAttemptModel.job_id == self._ensure_uuid(job_id))
            .order_by(ValidationAttemptModel.attempt_number.desc(), ValidationAttemptModel.created_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def create_quarantine_record(
        self,
        *,
        quarantine_record_id: UUID | str | None = None,
        job_id: UUID | str,
        file_id: UUID | str,
        watcher_id: UUID | str,
        schema_version: str,
        source_display_path: str,
        quarantine_locator: str,
        reason_code: str,
        copy_status: str,
        operator_message: str,
        correlation_id: UUID | str,
        validation_attempt_id: UUID | str | None = None,
        source_sha256: str | None = None,
        quarantine_display_path: str | None = None,
        checksum_sha256: str | None = None,
        copied_size_bytes: int | None = None,
    ) -> QuarantineRecordModel:
        record = QuarantineRecordModel(
            quarantine_record_id=self._ensure_uuid(quarantine_record_id),
            job_id=self._ensure_uuid(job_id),
            file_id=self._ensure_uuid(file_id),
            watcher_id=self._ensure_uuid(watcher_id),
            validation_attempt_id=None
            if validation_attempt_id is None
            else self._ensure_uuid(validation_attempt_id),
            schema_version=schema_version,
            source_display_path=source_display_path,
            source_sha256=source_sha256,
            quarantine_locator=quarantine_locator,
            quarantine_display_path=quarantine_display_path,
            reason_code=reason_code,
            copy_status=copy_status,
            checksum_sha256=checksum_sha256,
            copied_size_bytes=copied_size_bytes,
            operator_message=operator_message,
            correlation_id=self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_quarantine_records(self, *, job_id: UUID | str | None = None) -> list[QuarantineRecordModel]:
        statement = sa.select(QuarantineRecordModel)
        if job_id is not None:
            statement = statement.where(QuarantineRecordModel.job_id == self._ensure_uuid(job_id))
        statement = statement.order_by(QuarantineRecordModel.created_at.desc())
        return list(self.session.scalars(statement))


__all__ = ["ValidationRepository"]
