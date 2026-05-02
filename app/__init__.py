"""Shared Stream Lite application primitives for WP-01."""

from __future__ import annotations

import uuid
from uuid import UUID

_UUID_FACTORY = getattr(uuid, "uuid7", uuid.uuid4)


def generate_uuid() -> UUID:
    """Return an application-owned UUID before any persistence side effects."""

    return _UUID_FACTORY()


def generate_uuid_str() -> str:
    """Return a lowercase canonical UUID string."""

    return str(generate_uuid())


def ensure_uuid_str(value: UUID | str | None, *, field_name: str = "uuid") -> str:
    """Normalize an existing UUID value or generate a new one when missing."""

    if value is None:
        return generate_uuid_str()
    if isinstance(value, UUID):
        return str(value)
    try:
        return str(UUID(str(value)))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid UUID string") from exc


__all__ = ["ensure_uuid_str", "generate_uuid", "generate_uuid_str"]
