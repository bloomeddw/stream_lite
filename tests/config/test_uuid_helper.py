from __future__ import annotations

from uuid import UUID

from app import ensure_uuid_str, generate_uuid, generate_uuid_str


def test_uuid_helper_generates_canonical_application_owned_ids() -> None:
    first = generate_uuid()
    second = generate_uuid_str()

    assert isinstance(first, UUID)
    assert str(first) == ensure_uuid_str(first)
    assert second == ensure_uuid_str(second)
    assert UUID(second).version in {4, 7}
    assert str(first) != second
