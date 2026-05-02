"""Control-command and idempotency persistence primitives."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa

from app.db.models import ControlCommandModel, IdempotencyKeyModel

from .base import RepositoryBase


class CommandRepository(RepositoryBase):
    def create_command(
        self,
        *,
        command_id: UUID | str | None = None,
        command_type: str,
        target_resource_type: str,
        target_resource_id: UUID | str,
        requested_by: str,
        operator_reason: str,
        idempotency_key: str,
        correlation_id: UUID | str,
        status: str = "accepted",
    ) -> ControlCommandModel:
        record = ControlCommandModel(
            command_id=self._ensure_uuid(command_id),
            command_type=command_type,
            target_resource_type=target_resource_type,
            target_resource_id=self._ensure_uuid(target_resource_id),
            requested_by=requested_by,
            operator_reason=operator_reason,
            idempotency_key=idempotency_key,
            status=status,
            correlation_id=self._ensure_uuid(correlation_id),
        )
        self.session.add(record)
        self.session.flush()
        return record

    def get_command(self, command_id: UUID | str) -> ControlCommandModel | None:
        return self.session.get(ControlCommandModel, self._ensure_uuid(command_id))

    def update_command_status(
        self,
        command_id: UUID | str,
        *,
        status: str,
        result_locator: str | None = None,
        error_code: str | None = None,
        completed_at: datetime | None = None,
    ) -> ControlCommandModel:
        record = self.get_command(command_id)
        if record is None:
            raise ValueError("command not found")
        record.status = status
        record.result_locator = result_locator
        record.error_code = error_code
        if completed_at is not None or status in {"succeeded", "failed", "expired"}:
            record.completed_at = completed_at or self._now()
        record.updated_at = self._now()
        self.session.flush()
        return record

    def record_key(
        self,
        *,
        idempotency_key_id: UUID | str | None = None,
        scope: str,
        idempotency_key: str,
        target_type: str,
        target_id: UUID | str,
        payload_hash: str | None = None,
        first_response_json: dict[str, object] | None = None,
        expires_at: datetime | None = None,
        duplicate_detected_at: datetime | None = None,
    ) -> IdempotencyKeyModel:
        record = IdempotencyKeyModel(
            idempotency_key_id=self._ensure_uuid(idempotency_key_id),
            scope=scope,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            target_type=target_type,
            target_id=self._ensure_uuid(target_id),
            first_response_json=first_response_json,
            expires_at=expires_at,
            duplicate_detected_at=duplicate_detected_at,
        )
        self.session.add(record)
        self.session.flush()
        return record

    def reserve_idempotency_key(self, **kwargs: object) -> IdempotencyKeyModel:
        return self.record_key(**kwargs)

    def get_key(self, *, scope: str, idempotency_key: str) -> IdempotencyKeyModel | None:
        statement = sa.select(IdempotencyKeyModel).where(
            IdempotencyKeyModel.scope == scope,
            IdempotencyKeyModel.idempotency_key == idempotency_key,
        )
        return self.session.scalar(statement)

    def get_existing_result(self, *, scope: str, idempotency_key: str) -> dict[str, object] | None:
        record = self.get_key(scope=scope, idempotency_key=idempotency_key)
        return None if record is None else record.first_response_json


__all__ = ["CommandRepository"]
