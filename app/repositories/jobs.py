"""Job and state-history persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import JOB_STATE, TERMINAL_JOB_STATES, JobModel, JobStateHistoryModel

from .base import RepositoryBase

ALLOWED_JOB_TRANSITIONS: dict[str, set[str]] = {
    "DETECTED": {"STABILIZING", "FAILED"},
    "STABILIZING": {"REGISTERED", "FAILED"},
    "REGISTERED": {"VALIDATING", "FAILED"},
    "VALIDATING": {"VALIDATED", "INVALID", "FAILED"},
    "VALIDATED": {"PROCESSING", "FAILED"},
    "PROCESSING": {"PROCESSED", "RETRY_PENDING", "FAILED"},
    "PROCESSED": {"DELIVERING", "FAILED"},
    "DELIVERING": {"DELIVERED", "COMPLETED_WITH_DELIVERY_ERRORS", "RETRY_PENDING", "FAILED"},
    "DELIVERED": {"COMPLETED"},
    "INVALID": {"QUARANTINED"},
    "RETRY_PENDING": {"VALIDATING", "PROCESSING", "DELIVERING", "FAILED"},
    "COMPLETED_WITH_DELIVERY_ERRORS": set(),
    "COMPLETED": set(),
    "FAILED": set(),
    "QUARANTINED": set(),
}


class JobRepository(RepositoryBase):
    def create_job(
        self,
        *,
        job_id: UUID | str | None = None,
        file_id: UUID | str,
        watcher_id: UUID | str,
        source_folder_id: UUID | str,
        source_display_path: str,
        source_container_locator: str,
        source_file_name: str,
        source_extension: str,
        source_size_bytes: int,
        detected_at: datetime,
        correlation_id: UUID | str,
        state: str,
        stable_at: datetime | None = None,
        source_sha256: str | None = None,
        attempt_number: int = 0,
        latest_error_code: str | None = None,
    ) -> JobModel:
        record = JobModel(
            job_id=self._ensure_uuid(job_id),
            file_id=self._ensure_uuid(file_id),
            watcher_id=self._ensure_uuid(watcher_id),
            source_folder_id=self._ensure_uuid(source_folder_id),
            source_display_path=source_display_path,
            source_container_locator=source_container_locator,
            source_file_name=source_file_name,
            source_extension=source_extension,
            source_size_bytes=source_size_bytes,
            source_sha256=source_sha256,
            detected_at=detected_at,
            stable_at=stable_at,
            state=state,
            terminal_state=state if state in TERMINAL_JOB_STATES else None,
            attempt_number=attempt_number,
            correlation_id=self._ensure_uuid(correlation_id),
            latest_error_code=latest_error_code,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_job(self, job_id: UUID | str) -> JobModel | None:
        return self.session.get(JobModel, self._ensure_uuid(job_id))

    def list_jobs(
        self,
        *,
        state: str | None = None,
        watcher_id: UUID | str | None = None,
        file_name: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        terminal_state: str | None = None,
    ) -> list[JobModel]:
        statement = sa.select(JobModel)
        if state is not None:
            statement = statement.where(JobModel.state == state)
        if watcher_id is not None:
            statement = statement.where(JobModel.watcher_id == self._ensure_uuid(watcher_id))
        if file_name is not None:
            statement = statement.where(JobModel.source_file_name == file_name)
        if created_after is not None:
            statement = statement.where(JobModel.created_at >= created_after)
        if created_before is not None:
            statement = statement.where(JobModel.created_at <= created_before)
        if terminal_state is not None:
            statement = statement.where(JobModel.terminal_state == terminal_state)
        statement = statement.order_by(JobModel.created_at.desc(), JobModel.job_id.desc())
        return list(self.session.scalars(statement))

    def update_state(
        self,
        job_id: UUID | str,
        *,
        new_state: str,
        latest_error_code: str | None = None,
        attempt_number: int | None = None,
    ) -> JobModel:
        job = self.get_job(job_id)
        if job is None:
            raise ValueError("job not found")

        allowed_next_states = ALLOWED_JOB_TRANSITIONS.get(job.state, set())
        if new_state != job.state and new_state not in allowed_next_states:
            raise ValueError(f"invalid state transition: {job.state} -> {new_state}")

        job.state = new_state
        job.terminal_state = new_state if new_state in TERMINAL_JOB_STATES else None
        if latest_error_code is not None:
            job.latest_error_code = latest_error_code
        if attempt_number is not None:
            job.attempt_number = attempt_number
        job.updated_at = self._now()
        self.session.flush()
        return job

    def append_state_history(
        self,
        *,
        history_id: UUID | str | None = None,
        job_id: UUID | str,
        previous_state: str | None,
        new_state: str,
        actor_service: str,
        reason_code: str,
        correlation_id: UUID | str,
        transitioned_at: datetime,
        event_id: UUID | str | None = None,
        transition_sequence: int | None = None,
    ) -> JobStateHistoryModel:
        normalized_job_id = self._ensure_uuid(job_id)
        if transition_sequence is None:
            sequence_statement = sa.select(sa.func.max(JobStateHistoryModel.transition_sequence)).where(
                JobStateHistoryModel.job_id == normalized_job_id,
            )
            current_max = self.session.scalar(sequence_statement)
            transition_sequence = 1 if current_max is None else int(current_max) + 1

        record = JobStateHistoryModel(
            history_id=self._ensure_uuid(history_id),
            job_id=normalized_job_id,
            previous_state=previous_state,
            new_state=new_state,
            actor_service=actor_service,
            reason_code=reason_code,
            transition_sequence=transition_sequence,
            event_id=None if event_id is None else self._ensure_uuid(event_id),
            transitioned_at=transitioned_at,
            correlation_id=self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def append_state_transition(self, **kwargs: object) -> JobStateHistoryModel:
        return self.append_state_history(**kwargs)

    def list_state_history(self, job_id: UUID | str) -> list[JobStateHistoryModel]:
        statement = (
            sa.select(JobStateHistoryModel)
            .where(JobStateHistoryModel.job_id == self._ensure_uuid(job_id))
            .order_by(JobStateHistoryModel.transition_sequence.asc(), JobStateHistoryModel.transitioned_at.asc())
        )
        return list(self.session.scalars(statement))


__all__ = ["ALLOWED_JOB_TRANSITIONS", "JobRepository"]
