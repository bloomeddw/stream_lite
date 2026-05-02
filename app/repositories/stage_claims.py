"""Stage ownership claim persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import StageOwnershipClaimModel

from .base import RepositoryBase


class StageClaimRepository(RepositoryBase):
    def claim_stage(
        self,
        *,
        claim_id: UUID | str | None = None,
        job_id: UUID | str,
        stage: str,
        attempt_number: int,
        owner_service: str,
        lease_expires_at: datetime,
        correlation_id: UUID | str | None = None,
    ) -> StageOwnershipClaimModel:
        normalized_job_id = self._ensure_uuid(job_id)
        statement = sa.select(StageOwnershipClaimModel).where(
            StageOwnershipClaimModel.job_id == normalized_job_id,
            StageOwnershipClaimModel.stage == stage,
            StageOwnershipClaimModel.attempt_number == attempt_number,
        )
        existing = self.session.scalar(statement)
        now = self._now()
        if existing is None:
            record = StageOwnershipClaimModel(
                claim_id=self._ensure_uuid(claim_id),
                job_id=normalized_job_id,
                stage=stage,
                attempt_number=attempt_number,
                owner_service=owner_service,
                lease_expires_at=lease_expires_at,
                claim_status="active",
                correlation_id=None if correlation_id is None else self._ensure_uuid(correlation_id),
            )
            self.session.add(record)
            self.session.flush()
            return record

        if existing.claim_status == "active" and existing.lease_expires_at > now:
            raise ValueError("stage is already claimed")

        existing.owner_service = owner_service
        existing.lease_expires_at = lease_expires_at
        existing.claim_status = "active"
        existing.recovered_at = now
        existing.recovered_by_service = owner_service
        existing.released_at = None
        if correlation_id is not None:
            existing.correlation_id = self._ensure_uuid(correlation_id)
        existing.updated_at = now
        self.session.flush()
        return existing

    def renew_claim(self, claim_id: UUID | str, *, lease_expires_at: datetime) -> StageOwnershipClaimModel:
        record = self.session.get(StageOwnershipClaimModel, self._ensure_uuid(claim_id))
        if record is None:
            raise ValueError("stage claim not found")
        record.lease_expires_at = lease_expires_at
        record.updated_at = self._now()
        self.session.flush()
        return record

    def release_stage(
        self,
        claim_id: UUID | str,
        *,
        released_at: datetime | None = None,
    ) -> StageOwnershipClaimModel:
        record = self.session.get(StageOwnershipClaimModel, self._ensure_uuid(claim_id))
        if record is None:
            raise ValueError("stage claim not found")
        record.claim_status = "released"
        record.released_at = released_at or self._now()
        record.updated_at = self._now()
        self.session.flush()
        return record

    def release_claim(self, claim_id: UUID | str, **kwargs: object) -> StageOwnershipClaimModel:
        return self.release_stage(claim_id, **kwargs)

    def expire_claims(self, *, as_of: datetime | None = None) -> int:
        boundary = as_of or self._now()
        statement = (
            sa.update(StageOwnershipClaimModel)
            .where(StageOwnershipClaimModel.claim_status == "active")
            .where(StageOwnershipClaimModel.lease_expires_at < boundary)
            .values(claim_status="expired", updated_at=boundary)
        )
        result = self.session.execute(statement)
        self.session.flush()
        return int(result.rowcount or 0)

    def recover_expired_claims(self, *, as_of: datetime | None = None) -> int:
        return self.expire_claims(as_of=as_of)


__all__ = ["StageClaimRepository"]
