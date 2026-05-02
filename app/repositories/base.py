"""Shared repository primitives for SQLAlchemy-backed persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app import generate_uuid


class RepositoryBase:
    """Small base class shared by repository implementations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _ensure_uuid(value: UUID | str | None) -> UUID:
        if value is None:
            return generate_uuid()
        if isinstance(value, UUID):
            return value
        return UUID(str(value))


__all__ = ["RepositoryBase"]
