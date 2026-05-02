"""Delivery attempt and manifest persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.db.models import DeliveryAttemptModel, OutputManifestModel

from .base import RepositoryBase


class DeliveryRepository(RepositoryBase):
    def create_output_manifest(
        self,
        *,
        output_manifest_id: UUID | str | None = None,
        job_id: UUID | str,
        watcher_id: UUID | str,
        schema_version: str,
        manifest_locator: str,
        processing_summary_locator: str,
        produced_output_locators: list[str],
        source_sha256: str,
        destination_outcomes: list[dict[str, object]],
        finalized_at: datetime,
        status: str,
        correlation_id: UUID | str,
        output_sha256: str | None = None,
    ) -> OutputManifestModel:
        record = OutputManifestModel(
            output_manifest_id=self._ensure_uuid(output_manifest_id),
            job_id=self._ensure_uuid(job_id),
            watcher_id=self._ensure_uuid(watcher_id),
            schema_version=schema_version,
            manifest_locator=manifest_locator,
            processing_summary_locator=processing_summary_locator,
            produced_output_locators=produced_output_locators,
            source_sha256=source_sha256,
            output_sha256=output_sha256,
            destination_outcomes=destination_outcomes,
            finalized_at=finalized_at,
            status=status,
            correlation_id=self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_output_manifest(self, output_manifest_id: UUID | str) -> OutputManifestModel | None:
        return self.session.get(OutputManifestModel, self._ensure_uuid(output_manifest_id))

    def create_delivery_attempt(
        self,
        *,
        delivery_attempt_id: UUID | str | None = None,
        job_id: UUID | str,
        destination_folder_id: UUID | str,
        attempt_number: int,
        matched_route_tags: list[str],
        started_at: datetime,
        correlation_id: UUID | str,
        status: str = "pending",
        temporary_locator: str | None = None,
    ) -> DeliveryAttemptModel:
        record = DeliveryAttemptModel(
            delivery_attempt_id=self._ensure_uuid(delivery_attempt_id),
            job_id=self._ensure_uuid(job_id),
            destination_folder_id=self._ensure_uuid(destination_folder_id),
            attempt_number=attempt_number,
            matched_route_tags=matched_route_tags,
            temporary_locator=temporary_locator,
            status=status,
            started_at=started_at,
            correlation_id=self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def complete_delivery_attempt(
        self,
        delivery_attempt_id: UUID | str,
        *,
        finalized_locator: str,
        manifest_locator: str,
        checksum_sha256: str,
        completed_at: datetime,
    ) -> DeliveryAttemptModel:
        record = self.session.get(DeliveryAttemptModel, self._ensure_uuid(delivery_attempt_id))
        if record is None:
            raise ValueError("delivery attempt not found")
        record.finalized_locator = finalized_locator
        record.manifest_locator = manifest_locator
        record.checksum_sha256 = checksum_sha256
        record.completed_at = completed_at
        record.status = "delivered"
        record.updated_at = self._now()
        self.session.flush()
        return record

    def fail_delivery_attempt(
        self,
        delivery_attempt_id: UUID | str,
        *,
        failure_code: str,
        completed_at: datetime,
        manifest_locator: str | None = None,
    ) -> DeliveryAttemptModel:
        record = self.session.get(DeliveryAttemptModel, self._ensure_uuid(delivery_attempt_id))
        if record is None:
            raise ValueError("delivery attempt not found")
        record.failure_code = failure_code
        record.completed_at = completed_at
        record.manifest_locator = manifest_locator
        record.status = "failed"
        record.updated_at = self._now()
        self.session.flush()
        return record


__all__ = ["DeliveryRepository"]
