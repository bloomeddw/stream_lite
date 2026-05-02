"""File identity and duplicate-observation persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import DuplicateSuppressionObservationModel, FileModel

from .base import RepositoryBase


class FileRepository(RepositoryBase):
    def create_file_record(
        self,
        *,
        file_id: UUID | str | None = None,
        watcher_id: UUID | str,
        source_folder_id: UUID | str,
        source_display_path: str,
        source_container_locator: str,
        file_name: str,
        file_extension: str,
        size_bytes: int,
        deduplication_key: str,
        first_seen_at: datetime,
        stable_at: datetime | None = None,
        sha256: str | None = None,
    ) -> FileModel:
        record = FileModel(
            file_id=self._ensure_uuid(file_id),
            watcher_id=self._ensure_uuid(watcher_id),
            source_folder_id=self._ensure_uuid(source_folder_id),
            source_display_path=source_display_path,
            source_container_locator=source_container_locator,
            file_name=file_name,
            file_extension=file_extension,
            size_bytes=size_bytes,
            deduplication_key=deduplication_key,
            first_seen_at=first_seen_at,
            stable_at=stable_at,
            sha256=sha256,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_file_record(self, file_id: UUID | str) -> FileModel | None:
        return self.session.get(FileModel, self._ensure_uuid(file_id))

    def find_by_deduplication_key(self, deduplication_key: str) -> FileModel | None:
        statement = sa.select(FileModel).where(FileModel.deduplication_key == deduplication_key)
        return self.session.scalar(statement)

    def get_by_deduplication_key(self, deduplication_key: str) -> FileModel | None:
        return self.find_by_deduplication_key(deduplication_key)

    def record_duplicate_observation(
        self,
        *,
        duplicate_observation_id: UUID | str | None = None,
        existing_job_id: UUID | str,
        watcher_id: UUID | str,
        source_folder_id: UUID | str,
        source_display_path: str,
        byte_size: int,
        observed_at: datetime,
        reason_code: str,
        content_hash: str | None = None,
    ) -> DuplicateSuppressionObservationModel:
        record = DuplicateSuppressionObservationModel(
            duplicate_observation_id=self._ensure_uuid(duplicate_observation_id),
            existing_job_id=self._ensure_uuid(existing_job_id),
            watcher_id=self._ensure_uuid(watcher_id),
            source_folder_id=self._ensure_uuid(source_folder_id),
            source_display_path=source_display_path,
            byte_size=byte_size,
            content_hash=content_hash,
            observed_at=observed_at,
            reason_code=reason_code,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def list_duplicate_observations(
        self,
        *,
        existing_job_id: UUID | str | None = None,
    ) -> list[DuplicateSuppressionObservationModel]:
        statement = sa.select(DuplicateSuppressionObservationModel)
        if existing_job_id is not None:
            statement = statement.where(
                DuplicateSuppressionObservationModel.existing_job_id == self._ensure_uuid(existing_job_id),
            )
        statement = statement.order_by(
            DuplicateSuppressionObservationModel.observed_at.desc(),
            DuplicateSuppressionObservationModel.duplicate_observation_id.desc(),
        )
        return list(self.session.scalars(statement))


__all__ = ["FileRepository"]
