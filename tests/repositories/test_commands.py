from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app import generate_uuid
from app.repositories.commands import CommandRepository


def test_idempotency_key_unique_constraint(db_session) -> None:
    repo = CommandRepository(db_session)
    repo.record_key(
        idempotency_key_id=generate_uuid(),
        scope="jobs.retry",
        idempotency_key="retry-key-001",
        target_type="job",
        target_id=generate_uuid(),
        payload_hash="payload-1",
    )

    with pytest.raises(IntegrityError):
        repo.record_key(
            idempotency_key_id=generate_uuid(),
            scope="jobs.retry",
            idempotency_key="retry-key-001",
            target_type="job",
            target_id=generate_uuid(),
            payload_hash="payload-2",
        )
        db_session.flush()
