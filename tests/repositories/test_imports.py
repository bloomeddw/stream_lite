from __future__ import annotations

from app.repositories import (
    CommandRepository,
    DeliveryRepository,
    EventOffsetRepository,
    EventOutboxRepository,
    FileRepository,
    HealthRepository,
    JobRepository,
    OperationalLogRepository,
    ProcessingRepository,
    RetryRepository,
    StageClaimRepository,
    ValidationRepository,
    WatcherRepository,
)


def test_repository_surfaces_import() -> None:
    assert CommandRepository
    assert DeliveryRepository
    assert EventOffsetRepository
    assert EventOutboxRepository
    assert FileRepository
    assert HealthRepository
    assert JobRepository
    assert OperationalLogRepository
    assert ProcessingRepository
    assert RetryRepository
    assert StageClaimRepository
    assert ValidationRepository
    assert WatcherRepository
