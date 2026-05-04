from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from app import generate_uuid
from app.db.models import (
    DeliveryAttemptModel,
    EventOutboxModel,
    ProcessingAttemptModel,
    RetryScheduleModel,
)
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.retry import RetryRepository
from app.repositories.watchers import WatcherRepository
from app.retry import BackoffPolicy, RetryScheduler


@dataclass(slots=True)
class FrozenClock:
    current: datetime

    def now(self) -> datetime:
        return self.current


def test_retryable_processing_failure_schedules_retry_transitions_job_and_enqueues_event(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(db_session, state="PROCESSING", attempt_number=1)

    result = scheduler.schedule_retry_for_job(
        seeded["job"].job_id,
        failed_stage="processing",
        error_code="PROCESSOR_TIMEOUT",
    )

    job = seeded["jobs"].get_job(seeded["job"].job_id)
    schedule = db_session.query(RetryScheduleModel).one()
    history = seeded["jobs"].list_state_history(seeded["job"].job_id)
    event = _list_events(db_session)[0]

    assert result.status == "scheduled"
    assert result.reason_code == "RETRY_SCHEDULED"
    assert job is not None and job.state == "RETRY_PENDING"
    assert job.attempt_number == 2
    assert job.latest_error_code == "PROCESSOR_TIMEOUT"
    assert schedule.failed_stage == "processing"
    assert schedule.failure_class == "retryable"
    assert schedule.attempt_number == 2
    assert schedule.max_attempts == 3
    assert schedule.jitter_enabled is False
    assert schedule.next_stage == "processing"
    assert schedule.last_error_code == "PROCESSOR_TIMEOUT"
    assert schedule.backoff_seconds == 1.0
    assert _as_utc(schedule.due_at) == clock.now() + timedelta(seconds=1)
    assert history[-1].previous_state == "PROCESSING"
    assert history[-1].new_state == "RETRY_PENDING"
    assert history[-1].actor_service == "retry_scheduler"
    assert history[-1].reason_code == "RETRY_SCHEDULED"
    assert event.event_type == "retry.scheduled"
    assert event.stream_name == "stream_lite.lifecycle"
    assert event.producer == "retry_scheduler"
    assert event.attempt_number == 2
    assert event.idempotency_key == f"retry.scheduled:{seeded['job'].job_id}:processing:2"
    assert event.payload_json == {
        "next_stage": "processing",
        "due_at": "2026-05-03T12:00:01Z",
        "backoff_seconds": 1.0,
        "max_attempts": 3,
        "retry_reason": "Processing timed out and a retry can be scheduled.",
    }


def test_retryable_delivery_failure_schedules_retry(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 12, 15, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(db_session, state="DELIVERING", attempt_number=1)

    result = scheduler.schedule_retry_for_job(
        seeded["job"].job_id,
        failed_stage="delivery",
        error_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
    )

    job = seeded["jobs"].get_job(seeded["job"].job_id)
    schedule = db_session.query(RetryScheduleModel).one()
    event = _list_events(db_session)[0]

    assert result.status == "scheduled"
    assert job is not None and job.state == "RETRY_PENDING"
    assert job.attempt_number == 2
    assert schedule.next_stage == "delivery"
    assert _as_utc(schedule.due_at) == clock.now() + timedelta(seconds=1)
    assert event.event_type == "retry.scheduled"
    assert event.payload_json["next_stage"] == "delivery"
    assert event.idempotency_key == f"retry.scheduled:{seeded['job'].job_id}:delivery:2"


def test_non_retryable_validation_failure_transitions_to_quarantined_without_schedule(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 12, 30, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(db_session, state="INVALID", attempt_number=1)

    result = scheduler.schedule_retry_for_job(
        seeded["job"].job_id,
        failed_stage="validation",
        error_code="SCHEMA_INVALID",
    )

    job = seeded["jobs"].get_job(seeded["job"].job_id)
    history = seeded["jobs"].list_state_history(seeded["job"].job_id)

    assert result.status == "terminal"
    assert result.reason_code == "NON_RETRYABLE_FAILURE"
    assert job is not None and job.state == "QUARANTINED"
    assert db_session.query(RetryScheduleModel).count() == 0
    assert db_session.query(EventOutboxModel).count() == 0
    assert history[-1].previous_state == "INVALID"
    assert history[-1].new_state == "QUARANTINED"
    assert history[-1].reason_code == "NON_RETRYABLE_FAILURE"


def test_non_retryable_processing_failure_transitions_to_failed_and_enqueues_job_failed(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 12, 45, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(db_session, state="PROCESSING", attempt_number=1)

    result = scheduler.schedule_retry_for_job(
        seeded["job"].job_id,
        failed_stage="processing",
        error_code="PROCESSING_INPUT_INVALID",
    )

    job = seeded["jobs"].get_job(seeded["job"].job_id)
    history = seeded["jobs"].list_state_history(seeded["job"].job_id)
    event = _list_events(db_session)[0]

    assert result.status == "terminal"
    assert job is not None and job.state == "FAILED"
    assert db_session.query(RetryScheduleModel).count() == 0
    assert history[-1].previous_state == "PROCESSING"
    assert history[-1].new_state == "FAILED"
    assert history[-1].reason_code == "NON_RETRYABLE_FAILURE"
    assert event.event_type == "job.failed"
    assert event.idempotency_key == f"job.failed:{seeded['job'].job_id}:processing:1"
    assert event.payload_json == {
        "final_failure_class": "non_retryable",
        "exhausted_stage": "processing",
        "last_error_code": "PROCESSING_INPUT_INVALID",
        "operator_message": "Processing rejected invalid input and it will not be retried automatically.",
    }


def test_exhausted_retry_transitions_to_failed_and_enqueues_job_failed(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 13, 0, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(db_session, state="PROCESSING", attempt_number=3)

    result = scheduler.schedule_retry_for_job(
        seeded["job"].job_id,
        failed_stage="processing",
        error_code="PROCESSOR_TIMEOUT",
    )

    job = seeded["jobs"].get_job(seeded["job"].job_id)
    history = seeded["jobs"].list_state_history(seeded["job"].job_id)
    event = _list_events(db_session)[0]

    assert result.status == "exhausted"
    assert job is not None and job.state == "FAILED"
    assert db_session.query(RetryScheduleModel).count() == 0
    assert history[-1].new_state == "FAILED"
    assert history[-1].reason_code == "RETRY_EXHAUSTED"
    assert event.event_type == "job.failed"
    assert event.idempotency_key == f"job.failed:{seeded['job'].job_id}:processing:3"
    assert event.payload_json == {
        "final_failure_class": "exhausted_retries",
        "exhausted_stage": "processing",
        "last_error_code": "PROCESSOR_TIMEOUT",
        "operator_message": "Retry attempts are exhausted for the processing stage and the job has failed.",
    }


def test_due_retry_transitions_retry_pending_to_processing(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 13, 15, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(
        db_session,
        state="RETRY_PENDING",
        attempt_number=2,
        latest_error_code="PROCESSOR_TIMEOUT",
    )
    schedule = _seed_retry_schedule(
        db_session,
        job_id=seeded["job"].job_id,
        correlation_id=seeded["correlation_id"],
        failed_stage="processing",
        next_stage="processing",
        attempt_number=2,
        max_attempts=3,
        due_at=clock.now() - timedelta(seconds=5),
        last_error_code="PROCESSOR_TIMEOUT",
    )

    result = scheduler.process_due_retry(schedule.retry_schedule_id)

    job = seeded["jobs"].get_job(seeded["job"].job_id)
    history = seeded["jobs"].list_state_history(seeded["job"].job_id)
    updated_schedule = db_session.get(RetryScheduleModel, schedule.retry_schedule_id)

    assert result.status == "attempted"
    assert result.reason_code == "RETRY_DUE"
    assert job is not None and job.state == "PROCESSING"
    assert job.attempt_number == 2
    assert updated_schedule is not None and updated_schedule.status == "attempted"
    assert history[-1].previous_state == "RETRY_PENDING"
    assert history[-1].new_state == "PROCESSING"
    assert history[-1].reason_code == "RETRY_DUE"


def test_due_retry_transitions_retry_pending_to_delivering(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 13, 30, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(
        db_session,
        state="RETRY_PENDING",
        attempt_number=2,
        latest_error_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
    )
    schedule = _seed_retry_schedule(
        db_session,
        job_id=seeded["job"].job_id,
        correlation_id=seeded["correlation_id"],
        failed_stage="delivery",
        next_stage="delivery",
        attempt_number=2,
        max_attempts=3,
        due_at=clock.now() - timedelta(seconds=5),
        last_error_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
    )

    result = scheduler.process_due_retry(schedule.retry_schedule_id)

    job = seeded["jobs"].get_job(seeded["job"].job_id)

    assert result.status == "attempted"
    assert job is not None and job.state == "DELIVERING"


def test_due_retry_marks_schedule_attempted_and_does_not_run_worker_business_logic(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 13, 45, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(
        db_session,
        state="RETRY_PENDING",
        attempt_number=2,
        latest_error_code="PROCESSOR_TIMEOUT",
    )
    schedule = _seed_retry_schedule(
        db_session,
        job_id=seeded["job"].job_id,
        correlation_id=seeded["correlation_id"],
        failed_stage="processing",
        next_stage="processing",
        attempt_number=2,
        max_attempts=3,
        due_at=clock.now() - timedelta(seconds=1),
        last_error_code="PROCESSOR_TIMEOUT",
    )

    result = scheduler.process_due_retry(schedule.retry_schedule_id)
    updated_schedule = db_session.get(RetryScheduleModel, schedule.retry_schedule_id)

    assert result.status == "attempted"
    assert updated_schedule is not None and updated_schedule.status == "attempted"
    assert db_session.query(ProcessingAttemptModel).count() == 0
    assert db_session.query(DeliveryAttemptModel).count() == 0
    assert db_session.query(EventOutboxModel).count() == 0


def test_future_retry_is_skipped(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 14, 0, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(
        db_session,
        state="RETRY_PENDING",
        attempt_number=2,
        latest_error_code="PROCESSOR_TIMEOUT",
    )
    schedule = _seed_retry_schedule(
        db_session,
        job_id=seeded["job"].job_id,
        correlation_id=seeded["correlation_id"],
        failed_stage="processing",
        next_stage="processing",
        attempt_number=2,
        max_attempts=3,
        due_at=clock.now() + timedelta(seconds=30),
        last_error_code="PROCESSOR_TIMEOUT",
    )

    result = scheduler.process_due_retry(schedule.retry_schedule_id)
    job = seeded["jobs"].get_job(seeded["job"].job_id)
    updated_schedule = db_session.get(RetryScheduleModel, schedule.retry_schedule_id)

    assert result.status == "skipped"
    assert result.reason_code == "RETRY_NOT_DUE"
    assert job is not None and job.state == "RETRY_PENDING"
    assert updated_schedule is not None and updated_schedule.status == "scheduled"
    assert len(seeded["jobs"].list_state_history(seeded["job"].job_id)) == 1


def test_process_due_retries_returns_accurate_counts(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 14, 15, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    first = _seed_job(db_session, state="RETRY_PENDING", attempt_number=2, latest_error_code="PROCESSOR_TIMEOUT")
    second = _seed_job(
        db_session,
        state="RETRY_PENDING",
        attempt_number=2,
        latest_error_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
    )
    exhausted = _seed_job(db_session, state="RETRY_PENDING", attempt_number=4, latest_error_code="PROCESSOR_TIMEOUT")
    invalid = _seed_job(db_session, state="FAILED", attempt_number=2, latest_error_code="PROCESSOR_TIMEOUT")

    _seed_retry_schedule(
        db_session,
        job_id=first["job"].job_id,
        correlation_id=first["correlation_id"],
        failed_stage="processing",
        next_stage="processing",
        attempt_number=2,
        max_attempts=3,
        due_at=clock.now() - timedelta(seconds=1),
        last_error_code="PROCESSOR_TIMEOUT",
    )
    _seed_retry_schedule(
        db_session,
        job_id=second["job"].job_id,
        correlation_id=second["correlation_id"],
        failed_stage="delivery",
        next_stage="delivery",
        attempt_number=2,
        max_attempts=3,
        due_at=clock.now() - timedelta(seconds=1),
        last_error_code="DESTINATION_TEMPORARILY_UNAVAILABLE",
    )
    _seed_retry_schedule(
        db_session,
        job_id=exhausted["job"].job_id,
        correlation_id=exhausted["correlation_id"],
        failed_stage="processing",
        next_stage="processing",
        attempt_number=4,
        max_attempts=3,
        due_at=clock.now() - timedelta(seconds=1),
        last_error_code="PROCESSOR_TIMEOUT",
    )
    _seed_retry_schedule(
        db_session,
        job_id=invalid["job"].job_id,
        correlation_id=invalid["correlation_id"],
        failed_stage="processing",
        next_stage="processing",
        attempt_number=2,
        max_attempts=3,
        due_at=clock.now() - timedelta(seconds=1),
        last_error_code="PROCESSOR_TIMEOUT",
    )

    result = scheduler.process_due_retries(limit=10)

    assert result.scanned == 4
    assert result.attempted == 2
    assert result.exhausted == 1
    assert result.skipped == 0
    assert result.failed == 1


def test_correlation_id_is_preserved_in_schedule_history_and_events(db_session) -> None:
    clock = FrozenClock(datetime(2026, 5, 3, 14, 30, 0, tzinfo=timezone.utc))
    scheduler = _make_scheduler(db_session, clock)
    seeded = _seed_job(db_session, state="PROCESSING", attempt_number=1)
    correlation_id = str(uuid4())

    scheduler.schedule_retry_for_job(
        seeded["job"].job_id,
        failed_stage="processing",
        error_code="PROCESSOR_TIMEOUT",
        correlation_id=correlation_id,
    )

    schedule = db_session.query(RetryScheduleModel).one()
    history = seeded["jobs"].list_state_history(seeded["job"].job_id)[-1]
    event = _list_events(db_session)[0]

    assert schedule.correlation_id == UUID(correlation_id)
    assert history.correlation_id == UUID(correlation_id)
    assert event.correlation_id == UUID(correlation_id)


def _make_scheduler(db_session, clock: FrozenClock, *, max_attempts: int = 3) -> RetryScheduler:
    return RetryScheduler(
        retry_repository=RetryRepository(db_session),
        job_repository=JobRepository(db_session),
        event_repository=EventOutboxRepository(db_session),
        backoff_policy=BackoffPolicy(
            max_attempts=max_attempts,
            initial_backoff_seconds=1,
            multiplier=2.0,
            max_backoff_seconds=30,
            jitter_enabled=False,
        ),
        clock=clock.now,
    )


def _seed_job(
    db_session,
    *,
    state: str,
    attempt_number: int,
    latest_error_code: str | None = None,
) -> dict[str, object]:
    watchers = WatcherRepository(db_session)
    watcher = watchers.create_watcher(
        watcher_id=generate_uuid(),
        name=f"retry-watcher-{uuid4()}",
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
                "display_path": "/safe/source/retry",
                "normalized_path": "/data/sources/retry",
                "route_tags": ["RETRY"],
                "route_tags_text": "RETRY",
                "health_status": "green",
            },
        ],
    )[0]
    watchers.replace_destinations(
        watcher.watcher_id,
        destinations=[
            {
                "destination_folder_id": generate_uuid(),
                "display_path": "/safe/output/retry",
                "normalized_path": "/data/outputs/retry",
                "route_tags": ["RETRY"],
                "route_tags_text": "RETRY",
                "health_status": "green",
            },
        ],
    )

    correlation_id = str(uuid4())
    files = FileRepository(db_session)
    file_record = files.create_file_record(
        file_id=generate_uuid(),
        watcher_id=watcher.watcher_id,
        source_folder_id=source.source_folder_id,
        source_display_path="/safe/source/retry/example.csv",
        source_container_locator="/data/sources/retry/example.csv",
        file_name="example.csv",
        file_extension=".csv",
        size_bytes=128,
        deduplication_key=f"retry:{uuid4()}",
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
        source_display_path="/safe/source/retry/example.csv",
        source_container_locator="/data/sources/retry/example.csv",
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
    previous_state, actor_service, reason_code = _seed_transition_for_state(state)
    jobs.append_state_history(
        job_id=job.job_id,
        previous_state=previous_state,
        new_state=state,
        actor_service=actor_service,
        reason_code=reason_code,
        correlation_id=correlation_id,
        transitioned_at=_ts(8),
    )
    return {
        "correlation_id": correlation_id,
        "job": job,
        "jobs": jobs,
    }


def _seed_retry_schedule(
    db_session,
    *,
    job_id,
    correlation_id: str,
    failed_stage: str,
    next_stage: str,
    attempt_number: int,
    max_attempts: int,
    due_at: datetime,
    last_error_code: str,
) -> RetryScheduleModel:
    return RetryRepository(db_session).schedule_retry(
        job_id=job_id,
        failed_stage=failed_stage,
        failure_class="retryable",
        due_at=due_at,
        backoff_seconds=1.0,
        attempt_number=attempt_number,
        max_attempts=max_attempts,
        jitter_enabled=False,
        next_stage=next_stage,
        last_error_code=last_error_code,
        correlation_id=correlation_id,
    )


def _seed_transition_for_state(state: str) -> tuple[str | None, str, str]:
    if state == "PROCESSING":
        return "VALIDATED", "processor", "PROCESSING_STARTED"
    if state == "DELIVERING":
        return "PROCESSED", "delivery", "DELIVERY_STARTED"
    if state == "INVALID":
        return "VALIDATING", "validator", "SCHEMA_INVALID"
    if state == "RETRY_PENDING":
        return "PROCESSING", "retry_scheduler", "RETRY_SCHEDULED"
    if state == "FAILED":
        return "PROCESSING", "processor", "PROCESSOR_TIMEOUT"
    return None, "watcher", "STATE_SEEDED"


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
    return datetime(2026, 5, 3, hour, 0, 0, tzinfo=timezone.utc)
