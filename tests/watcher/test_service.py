from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.config.path_policy import PathPolicy
from app.config.settings import StreamLiteSettings
from app.db.models import EventOutboxModel, JobModel
from app.repositories.events import EventOutboxRepository
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.watchers import WatcherRepository
from app.watcher.service import WatcherService


class Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def monotonic(self) -> float:
        return self.value

    def now(self) -> datetime:
        return datetime(2026, 5, 1, 12, 0, int(self.value) % 60, tzinfo=timezone.utc)


def test_poll_once_registers_stable_file_and_outbox_events(db_session, tmp_path) -> None:
    service, watcher_id, clock = _make_service(db_session, tmp_path)
    source_file = tmp_path / "sources" / "source-a" / "input.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    first = service.poll_once(watcher_id, correlation_id=uuid4())
    assert first.jobs_registered == 0

    clock.value = 3.0
    second = service.poll_once(watcher_id, correlation_id=uuid4())

    assert second.observed_files == 1
    assert second.stabilized_files == 1
    assert second.jobs_registered == 1
    jobs = db_session.query(JobModel).all()
    assert len(jobs) == 1
    assert jobs[0].state == "REGISTERED"
    assert [row.new_state for row in JobRepository(db_session).list_state_history(jobs[0].job_id)] == [
        "DETECTED",
        "STABILIZING",
        "REGISTERED",
    ]
    events = db_session.query(EventOutboxModel).order_by(EventOutboxModel.occurred_at, EventOutboxModel.event_type).all()
    assert {event.event_type for event in events} == {"file.detected", "file.stable", "job.registered"}
    assert {event.stream_name for event in events} == {"stream_lite.lifecycle"}
    assert all(event.correlation_id for event in events)
    assert all(event.watcher_id == watcher_id for event in events)


def test_poll_once_empty_folder_and_inactive_watcher_create_no_jobs(db_session, tmp_path) -> None:
    service, watcher_id, _clock = _make_service(db_session, tmp_path)

    result = service.poll_once(watcher_id, correlation_id=uuid4())
    assert result.observed_files == 0
    assert result.jobs_registered == 0
    assert db_session.query(JobModel).count() == 0

    WatcherRepository(db_session).update_lifecycle_state(watcher_id, lifecycle_state="PAUSED", enabled=True)
    result = service.poll_once(watcher_id, correlation_id=uuid4())
    assert result.skipped_reason == "WATCHER_NOT_ACTIVE"
    assert db_session.query(JobModel).count() == 0


def test_duplicate_arrival_suppresses_job_and_events(db_session, tmp_path) -> None:
    service, watcher_id, clock = _make_service(db_session, tmp_path)
    source_file = tmp_path / "sources" / "source-a" / "input.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    service.poll_once(watcher_id, correlation_id=uuid4())
    clock.value = 3.0
    service.poll_once(watcher_id, correlation_id=uuid4())
    assert db_session.query(JobModel).count() == 1
    assert db_session.query(EventOutboxModel).count() == 3

    clock.value = 6.0
    service.poll_once(watcher_id, correlation_id=uuid4())
    clock.value = 9.0
    duplicate = service.poll_once(watcher_id, correlation_id=uuid4())

    assert duplicate.duplicates_suppressed == 1
    assert db_session.query(JobModel).count() == 1
    assert db_session.query(EventOutboxModel).count() == 3
    observations = FileRepository(db_session).list_duplicate_observations()
    assert len(observations) == 1
    assert observations[0].reason_code == "DUPLICATE_SUPPRESSED"


def test_outside_allowlist_source_path_is_skipped_without_host_path_leak(db_session, tmp_path) -> None:
    service, watcher_id, _clock = _make_service(db_session, tmp_path, source_path="/var/private/source-a")

    result = service.poll_once(watcher_id, correlation_id=uuid4())

    assert result.skipped_sources == 1
    assert db_session.query(JobModel).count() == 0
    rendered_logs = "\n".join(str(record) for record in service.log_records)
    assert "/var/private/source-a" not in rendered_logs
    assert "PATH_NOT_ALLOWLISTED" in rendered_logs


def _make_service(db_session, tmp_path, *, source_path: str | None = None):
    watch_root = tmp_path / "sources"
    output_root = tmp_path / "outputs"
    quarantine_root = tmp_path / "quarantine"
    source_root = watch_root / "source-a"
    destination_root = output_root / "destination-a"
    source_root.mkdir(parents=True, exist_ok=True)
    destination_root.mkdir(parents=True, exist_ok=True)
    quarantine_root.mkdir(parents=True, exist_ok=True)

    container_base = f"/stream-lite-test/{tmp_path.name}"
    container_watch_root = f"{container_base}/sources"
    container_output_root = f"{container_base}/outputs"
    container_quarantine_root = f"{container_base}/quarantine"
    container_source_root = f"{container_watch_root}/source-a"
    container_destination_root = f"{container_output_root}/destination-a"

    settings = StreamLiteSettings(
        api_port=8000,
        dashboard_port=8501,
        broker_profile="redis_streams",
        processing_engine="spark",
        watch_root=container_watch_root,
        output_root=container_output_root,
        quarantine_root=container_quarantine_root,
        database_url="postgresql://stream_lite:stream_lite@postgres:5432/stream_lite",
        redis_url="redis://redis:6379/0",
        debug=False,
        file_stability_seconds=2,
        max_file_size_mb=100,
        retry_max_attempts=3,
        retry_initial_backoff_seconds=1,
        retry_backoff_multiplier=2.0,
        retry_max_backoff_seconds=30,
        retry_jitter_enabled=True,
        dashboard_presentation_file="/app/config/dashboard_presentation.yaml",
        log_level="INFO",
        reconciliation_interval_seconds=10,
    )
    path_policy = PathPolicy(
        source_roots=(container_watch_root,),
        destination_roots=(container_output_root,),
        debug=False,
    )
    watcher_repository = WatcherRepository(db_session)
    watcher = watcher_repository.create_watcher(
        name="watcher-a",
        lifecycle_state="ACTIVE",
        operational_status="green",
        route_policy="tag_match_all_destinations",
        enabled=True,
    )
    source = watcher_repository.replace_sources(
        watcher.watcher_id,
        sources=[
            {
                "source_folder_id": uuid4(),
                "display_path": "/source-a",
                "normalized_path": source_path or container_source_root,
                "route_tags": ["A"],
                "route_tags_text": "A",
                "health_status": "green",
                "reason_code": None,
            },
        ],
    )[0]
    destination = watcher_repository.replace_destinations(
        watcher.watcher_id,
        destinations=[
            {
                "destination_folder_id": uuid4(),
                "display_path": "/destination-a",
                "normalized_path": container_destination_root,
                "route_tags": ["A"],
                "route_tags_text": "A",
                "health_status": "green",
                "reason_code": None,
            },
        ],
    )[0]
    watcher_repository.save_route_preview(
        watcher.watcher_id,
        route_matches=[
            {
                "route_match_id": uuid4(),
                "source_folder_id": source.source_folder_id,
                "destination_folder_id": destination.destination_folder_id,
                "route_policy": "tag_match_all_destinations",
                "matched_route_tags": ["A"],
                "unmatched_reason_code": None,
            },
        ],
    )
    def filesystem_resolver(container_path: str):
        if container_path == container_watch_root or container_path.startswith(f"{container_watch_root}/"):
            relative = container_path.removeprefix(container_watch_root).lstrip("/")
            return watch_root / relative
        if container_path == container_output_root or container_path.startswith(f"{container_output_root}/"):
            relative = container_path.removeprefix(container_output_root).lstrip("/")
            return output_root / relative
        if container_path == container_quarantine_root or container_path.startswith(f"{container_quarantine_root}/"):
            relative = container_path.removeprefix(container_quarantine_root).lstrip("/")
            return quarantine_root / relative
        return container_path

    clock = Clock()
    service = WatcherService(
        watcher_repository=watcher_repository,
        file_repository=FileRepository(db_session),
        job_repository=JobRepository(db_session),
        event_repository=EventOutboxRepository(db_session),
        path_policy=path_policy,
        settings=settings,
        monotonic=clock.monotonic,
        now=clock.now,
        filesystem_resolver=filesystem_resolver,
    )
    return service, watcher.watcher_id, clock
