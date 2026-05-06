from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app import generate_uuid
from app.db.models import ControlCommandModel, DeliveryAttemptModel, EventOutboxModel, ProcessingAttemptModel, RetryScheduleModel
from app.repositories.commands import CommandRepository
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.retry import RetryRepository
from app.repositories.watchers import WatcherRepository
from app.retry import BackoffPolicy, RetryClassifier, RetryScheduler
from app.retry.manual import ManualRetryError, ManualRetryService


@dataclass(slots=True)
class FrozenClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


def test_accepts_failed_processing_retryable_job_and_creates_schedule_state_history_event(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 4, 12, 0, 0, tzinfo=timezone.utc))
    service = _make_service(db_session, clock)
    seeded = _seed_job(
        db_session,
        state="FAILED",
        attempt_number=1,
        latest_error_code="PROCESSOR_TIMEOUT",
        previous_state="PROCESSING",
        reason_code="PROCESSOR_TIMEOUT",
    )
    _seed_processing_failure(
        db_session,
        job_id=seeded["job"].job_id,
        attempt_number=1,
        correlation_id=seeded["correlation_id"],
        error_code="PROCESSOR_TIMEOUT",
        completed_at=clock.now() - timedelta(minutes=1),
    )
    correlation_id = str(uuid4())

    result = service.accept_manual_retry_command(
        job_id=seeded["job"].job_id,
        requested_by="tester",
        operator_reason="operator retry",
        correlation_id=correlation_id,
    )

    command = CommandRepository(db_session).get_command(result.command_id)
    job = seeded["jobs"].get_job(seeded["job"].job_id)
    schedule = db_session.query(RetryScheduleModel).one()
    history = seeded["jobs"].list_state_history(seeded["job"].job_id)
    event = _list_events(db_session)[0]

    assert result.command_status == "succeeded"
    assert result.job_id == seeded["job"].job_id
    assert result.retry_schedule_id == schedule.retry_schedule_id
    assert result.failed_stage == "processing"
    assert result.attempt_number == 2
    assert result.manual_override is False
    assert command is not None and command.status == "succeeded"
    assert command.target_resource_id == seeded["job"].job_id
    assert command.result_locator == f"retry_schedule:{schedule.retry_schedule_id}"
    assert job is not None and job.state == "RETRY_PENDING"
    assert job.attempt_number == 2
    assert schedule.job_id == seeded["job"].job_id
    assert schedule.failed_stage == "processing"
    assert schedule.next_stage == "processing"
    assert schedule.attempt_number == 2
    assert schedule.backoff_seconds == 0.0
    assert _as_utc(schedule.due_at) == clock.now()
    assert history[-1].previous_state == "FAILED"
    assert history[-1].new_state == "RETRY_PENDING"
    assert history[-1].actor_service == "retry_scheduler"
    assert history[-1].reason_code == "MANUAL_RETRY_REQUESTED"
    assert history[-1].correlation_id == UUID(correlation_id)
    assert event.event_type == "retry.scheduled"
    assert event.idempotency_key == f"retry.scheduled:{seeded['job'].job_id}:manual:processing:2"
    assert event.payload_json == {
        "next_stage": "processing",
        "due_at": "2026-05-04T12:00:00Z",
        "backoff_seconds": 0.0,
        "max_attempts": 3,
        "retry_reason": "operator retry",
    }
    assert command.correlation_id == UUID(correlation_id)
    assert schedule.correlation_id == UUID(correlation_id)
    assert event.correlation_id == UUID(correlation_id)


def test_accepts_failed_delivery_retryable_job(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 4, 12, 15, 0, tzinfo=timezone.utc))
    service = _make_service(db_session, clock)
    seeded = _seed_job(
        db_session,
        state="FAILED",
        attempt_number=1,
        latest_error_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
        previous_state="DELIVERING",
        reason_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
    )
    _seed_delivery_failure(
        db_session,
        job_id=seeded["job"].job_id,
        destination_folder_id=seeded["destination_folder_id"],
        attempt_number=1,
        correlation_id=seeded["correlation_id"],
        error_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
        completed_at=clock.now() - timedelta(minutes=1),
    )

    result = service.accept_manual_retry_command(
        job_id=seeded["job"].job_id,
        requested_by="tester",
        operator_reason="delivery retry",
    )

    schedule = db_session.query(RetryScheduleModel).one()
    job = seeded["jobs"].get_job(seeded["job"].job_id)

    assert result.command_status == "succeeded"
    assert result.failed_stage == "delivery"
    assert result.attempt_number == 2
    assert result.manual_override is False
    assert job is not None and job.state == "RETRY_PENDING"
    assert job.attempt_number == 2
    assert schedule.failed_stage == "delivery"
    assert schedule.next_stage == "delivery"
    assert schedule.attempt_number == 2


@pytest.mark.parametrize(
    ("stage", "error_code"),
    [
        ("processing", "UNLISTED_PROCESSING_FAILURE"),
        ("delivery", "UNLISTED_DELIVERY_FAILURE"),
    ],
)
def test_accepts_manual_override_for_non_catalog_failure(db_session, stage: str, error_code: str) -> None:
    clock = FrozenClock(datetime(2026, 5, 4, 12, 30, 0, tzinfo=timezone.utc))
    service = _make_service(db_session, clock)
    previous_state = "PROCESSING" if stage == "processing" else "DELIVERING"
    latest_error_code = error_code
    seeded = _seed_job(
        db_session,
        state="FAILED",
        attempt_number=1,
        latest_error_code=latest_error_code,
        previous_state=previous_state,
        reason_code=latest_error_code,
    )
    if stage == "processing":
        _seed_processing_failure(
            db_session,
            job_id=seeded["job"].job_id,
            attempt_number=1,
            correlation_id=seeded["correlation_id"],
            error_code=error_code,
            completed_at=clock.now() - timedelta(minutes=1),
        )
    else:
        _seed_delivery_failure(
            db_session,
            job_id=seeded["job"].job_id,
            destination_folder_id=seeded["destination_folder_id"],
            attempt_number=1,
            correlation_id=seeded["correlation_id"],
            error_code=error_code,
            completed_at=clock.now() - timedelta(minutes=1),
        )

    result = service.accept_manual_retry_command(
        job_id=seeded["job"].job_id,
        requested_by="tester",
        operator_reason="operator override",
    )

    command = CommandRepository(db_session).get_command(result.command_id)
    assert result.command_status == "succeeded"
    assert result.manual_override is True
    assert result.failed_stage == stage
    assert command is not None and command.result_locator is not None
    assert command.result_locator.endswith("?manual_override=true")


def test_rejects_quarantined_validation_policy_job(db_session) -> None:
    service = _make_service(db_session, FrozenClock(datetime(2026, 5, 4, 12, 45, 0, tzinfo=timezone.utc)))
    seeded = _seed_job(
        db_session,
        state="QUARANTINED",
        attempt_number=1,
        latest_error_code="SCHEMA_INVALID",
        previous_state="INVALID",
        reason_code="SCHEMA_INVALID",
    )

    with pytest.raises(ManualRetryError) as excinfo:
        service.accept_manual_retry_command(
            job_id=seeded["job"].job_id,
            requested_by="tester",
            operator_reason="retry anyway",
        )

    assert excinfo.value.error_code == "JOB_NOT_RETRYABLE"
    assert excinfo.value.current_state == "QUARANTINED"


@pytest.mark.parametrize("state", ["COMPLETED", "RETRY_PENDING"])
def test_rejects_completed_and_retry_pending_jobs(db_session, state: str) -> None:
    service = _make_service(db_session, FrozenClock(datetime(2026, 5, 4, 13, 0, 0, tzinfo=timezone.utc)))
    previous_state = "DELIVERED" if state == "COMPLETED" else "FAILED"
    reason_code = "JOB_COMPLETED" if state == "COMPLETED" else "MANUAL_RETRY_REQUESTED"
    seeded = _seed_job(
        db_session,
        state=state,
        attempt_number=1,
        latest_error_code="PROCESSOR_TIMEOUT",
        previous_state=previous_state,
        reason_code=reason_code,
    )

    with pytest.raises(ManualRetryError) as excinfo:
        service.accept_manual_retry_command(
            job_id=seeded["job"].job_id,
            requested_by="tester",
            operator_reason="retry",
        )

    assert excinfo.value.error_code == "JOB_NOT_RETRYABLE"
    assert excinfo.value.current_state == state


@pytest.mark.parametrize("reason", [None, "   "])
def test_rejects_missing_or_blank_reason(db_session, reason: str | None) -> None:
    service = _make_service(db_session, FrozenClock(datetime(2026, 5, 4, 13, 15, 0, tzinfo=timezone.utc)))
    seeded = _seed_job(
        db_session,
        state="FAILED",
        attempt_number=1,
        latest_error_code="PROCESSOR_TIMEOUT",
        previous_state="PROCESSING",
        reason_code="PROCESSOR_TIMEOUT",
    )

    with pytest.raises(ManualRetryError) as excinfo:
        service.accept_manual_retry_command(
            job_id=seeded["job"].job_id,
            requested_by="tester",
            operator_reason=reason,
        )

    assert excinfo.value.error_code == "REQUEST_VALIDATION_FAILED"
    assert excinfo.value.field == "reason"


def test_rejects_exhausted_retry_count(db_session) -> None:
    service = _make_service(db_session, FrozenClock(datetime(2026, 5, 4, 13, 30, 0, tzinfo=timezone.utc)))
    seeded = _seed_job(
        db_session,
        state="FAILED",
        attempt_number=3,
        latest_error_code="PROCESSOR_TIMEOUT",
        previous_state="PROCESSING",
        reason_code="PROCESSOR_TIMEOUT",
    )
    _seed_processing_failure(
        db_session,
        job_id=seeded["job"].job_id,
        attempt_number=3,
        correlation_id=seeded["correlation_id"],
        error_code="PROCESSOR_TIMEOUT",
        completed_at=_ts(12),
    )

    with pytest.raises(ManualRetryError) as excinfo:
        service.accept_manual_retry_command(
            job_id=seeded["job"].job_id,
            requested_by="tester",
            operator_reason="retry exhausted job",
        )

    assert excinfo.value.error_code == "RETRY_LIMIT_EXHAUSTED"


def test_idempotency_same_key_same_payload_returns_first_command(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 4, 13, 45, 0, tzinfo=timezone.utc))
    service = _make_service(db_session, clock)
    seeded = _seed_job(
        db_session,
        state="FAILED",
        attempt_number=1,
        latest_error_code="PROCESSOR_TIMEOUT",
        previous_state="PROCESSING",
        reason_code="PROCESSOR_TIMEOUT",
    )
    _seed_processing_failure(
        db_session,
        job_id=seeded["job"].job_id,
        attempt_number=1,
        correlation_id=seeded["correlation_id"],
        error_code="PROCESSOR_TIMEOUT",
        completed_at=clock.now() - timedelta(minutes=1),
    )

    first = service.accept_manual_retry_command(
        job_id=seeded["job"].job_id,
        requested_by="tester",
        operator_reason="same request",
        idempotency_key="manual-retry-key",
        correlation_id=str(uuid4()),
    )
    second = service.accept_manual_retry_command(
        job_id=seeded["job"].job_id,
        requested_by="tester",
        operator_reason="same request",
        idempotency_key="manual-retry-key",
        correlation_id=str(uuid4()),
    )

    assert first.command_id == second.command_id
    assert second.idempotency_reused is True
    assert second.correlation_id == first.correlation_id
    assert db_session.query(ControlCommandModel).count() == 1
    assert db_session.query(RetryScheduleModel).count() == 1


def test_idempotency_same_key_different_payload_conflicts(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 4, 14, 0, 0, tzinfo=timezone.utc))
    service = _make_service(db_session, clock)
    seeded = _seed_job(
        db_session,
        state="FAILED",
        attempt_number=1,
        latest_error_code="PROCESSOR_TIMEOUT",
        previous_state="PROCESSING",
        reason_code="PROCESSOR_TIMEOUT",
    )
    _seed_processing_failure(
        db_session,
        job_id=seeded["job"].job_id,
        attempt_number=1,
        correlation_id=seeded["correlation_id"],
        error_code="PROCESSOR_TIMEOUT",
        completed_at=clock.now() - timedelta(minutes=1),
    )

    service.accept_manual_retry_command(
        job_id=seeded["job"].job_id,
        requested_by="tester",
        operator_reason="first payload",
        idempotency_key="manual-retry-conflict",
    )

    with pytest.raises(ManualRetryError) as excinfo:
        service.accept_manual_retry_command(
            job_id=seeded["job"].job_id,
            requested_by="tester",
            operator_reason="different payload",
            idempotency_key="manual-retry-conflict",
            correlation_id=str(uuid4()),
        )

    assert excinfo.value.error_code == "IDEMPOTENCY_KEY_CONFLICT"


def _make_service(db_session, clock: FrozenClock, *, max_attempts: int = 3) -> ManualRetryService:
    classifier = RetryClassifier()
    backoff_policy = BackoffPolicy(
        max_attempts=max_attempts,
        initial_backoff_seconds=1,
        multiplier=2.0,
        max_backoff_seconds=30,
        jitter_enabled=False,
    )
    retry_scheduler = RetryScheduler(
        retry_repository=RetryRepository(db_session),
        job_repository=JobRepository(db_session),
        event_repository=EventOutboxRepository(db_session),
        classifier=classifier,
        backoff_policy=backoff_policy,
        clock=clock.now,
    )
    return ManualRetryService(
        command_repository=CommandRepository(db_session),
        job_repository=JobRepository(db_session),
        retry_repository=RetryRepository(db_session),
        event_repository=EventOutboxRepository(db_session),
        retry_scheduler=retry_scheduler,
        classifier=classifier,
        backoff_policy=backoff_policy,
        clock=clock.now,
    )


def _seed_job(
    db_session,
    *,
    state: str,
    attempt_number: int,
    latest_error_code: str | None,
    previous_state: str | None,
    reason_code: str,
) -> dict[str, object]:
    watchers = WatcherRepository(db_session)
    watcher = watchers.create_watcher(
        watcher_id=generate_uuid(),
        name=f"manual-retry-{uuid4()}",
        lifecycle_state="CREATED",
        operational_status="green",
        route_policy="tag_match_all_destinations",
        enabled=True,
    )
    source = watchers.replace_sources(
        watcher.watcher_id,
        sources=[
            {
                "source_folder_id": generate_uuid(),
                "display_path": "/safe/source/manual",
                "normalized_path": "/data/sources/manual",
                "route_tags": ["MANUAL"],
                "route_tags_text": "MANUAL",
                "health_status": "green",
            },
        ],
    )[0]
    destination = watchers.replace_destinations(
        watcher.watcher_id,
        destinations=[
            {
                "destination_folder_id": generate_uuid(),
                "display_path": "/safe/output/manual",
                "normalized_path": "/data/outputs/manual",
                "route_tags": ["MANUAL"],
                "route_tags_text": "MANUAL",
                "health_status": "green",
            },
        ],
    )[0]
    watchers.save_route_preview(
        watcher.watcher_id,
        route_matches=[
            {
                "route_match_id": generate_uuid(),
                "source_folder_id": source.source_folder_id,
                "destination_folder_id": destination.destination_folder_id,
                "route_policy": "tag_match_all_destinations",
                "matched_route_tags": ["MANUAL"],
                "unmatched_reason_code": None,
            },
        ],
        previewed_at=_ts(8),
    )

    correlation_id = str(uuid4())
    file_record = FileRepository(db_session).create_file_record(
        file_id=generate_uuid(),
        watcher_id=watcher.watcher_id,
        source_folder_id=source.source_folder_id,
        source_display_path="/safe/source/manual/example.csv",
        source_container_locator="/data/sources/manual/example.csv",
        file_name="example.csv",
        file_extension=".csv",
        size_bytes=128,
        deduplication_key=f"manual:{uuid4()}",
        first_seen_at=_ts(8),
        stable_at=_ts(8),
        sha256="a" * 64,
    )

    jobs = JobRepository(db_session)
    job = jobs.create_job(
        job_id=generate_uuid(),
        file_id=file_record.file_id,
        watcher_id=watcher.watcher_id,
        source_folder_id=source.source_folder_id,
        source_display_path="/safe/source/manual/example.csv",
        source_container_locator="/data/sources/manual/example.csv",
        source_file_name="example.csv",
        source_extension=".csv",
        source_size_bytes=128,
        source_sha256="a" * 64,
        detected_at=_ts(8),
        stable_at=_ts(8),
        correlation_id=correlation_id,
        state=state,
        attempt_number=attempt_number,
        latest_error_code=latest_error_code,
    )
    jobs.append_state_history(
        job_id=job.job_id,
        previous_state=previous_state,
        new_state=state,
        actor_service=_actor_for_state(previous_state),
        reason_code=reason_code,
        correlation_id=correlation_id,
        transitioned_at=_ts(8),
    )
    return {
        "correlation_id": correlation_id,
        "destination_folder_id": destination.destination_folder_id,
        "job": job,
        "jobs": jobs,
    }


def _seed_processing_failure(
    db_session,
    *,
    job_id,
    attempt_number: int,
    correlation_id: str,
    error_code: str,
    completed_at: datetime,
) -> ProcessingAttemptModel:
    attempt = ProcessingAttemptModel(
        processing_attempt_id=generate_uuid(),
        job_id=job_id,
        attempt_number=attempt_number,
        engine="spark",
        engine_version="3.5.0",
        input_locator="/data/sources/manual/example.csv",
        started_at=completed_at - timedelta(minutes=1),
        completed_at=completed_at,
        duration_seconds=60.0,
        status="failed",
        error_code=error_code,
        correlation_id=UUID(correlation_id),
    )
    db_session.add(attempt)
    db_session.flush()
    return attempt


def _seed_delivery_failure(
    db_session,
    *,
    job_id,
    destination_folder_id,
    attempt_number: int,
    correlation_id: str,
    error_code: str,
    completed_at: datetime,
) -> DeliveryAttemptModel:
    attempt = DeliveryAttemptModel(
        delivery_attempt_id=generate_uuid(),
        job_id=job_id,
        destination_folder_id=destination_folder_id,
        attempt_number=attempt_number,
        matched_route_tags=["MANUAL"],
        status="failed",
        failure_code=error_code,
        started_at=completed_at - timedelta(minutes=1),
        completed_at=completed_at,
        correlation_id=UUID(correlation_id),
    )
    db_session.add(attempt)
    db_session.flush()
    return attempt


def _actor_for_state(previous_state: str | None) -> str:
    if previous_state == "PROCESSING":
        return "processor"
    if previous_state == "DELIVERING":
        return "delivery"
    if previous_state == "INVALID":
        return "validator"
    return "watcher"


def _list_events(db_session) -> list[EventOutboxModel]:
    return (
        db_session.query(EventOutboxModel)
        .order_by(EventOutboxModel.occurred_at.asc(), EventOutboxModel.event_type.asc())
        .all()
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _ts(hour: int) -> datetime:
    return datetime(2026, 5, 4, hour, 0, 0, tzinfo=timezone.utc)
