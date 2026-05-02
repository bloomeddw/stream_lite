from __future__ import annotations

from datetime import datetime, timezone

from app import generate_uuid
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.watchers import WatcherRepository


def _ts(hour: int) -> datetime:
    return datetime(2026, 4, 30, hour, 0, 0, tzinfo=timezone.utc)


def _create_watcher_graph(db_session) -> tuple[str, str, str]:
    watchers = WatcherRepository(db_session)
    watcher = watchers.create_watcher(
        watcher_id=generate_uuid(),
        name="demo-watcher",
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
                "display_path": "/safe/source/inbox",
                "normalized_path": "/data/sources/inbox",
                "route_tags": ["ALPHA"],
                "route_tags_text": "ALPHA",
                "health_status": "green",
            },
        ],
    )[0]
    destination = watchers.replace_destinations(
        watcher.watcher_id,
        destinations=[
            {
                "destination_folder_id": generate_uuid(),
                "display_path": "/safe/output/archive",
                "normalized_path": "/data/outputs/archive",
                "route_tags": ["ALPHA"],
                "route_tags_text": "ALPHA",
                "health_status": "green",
            },
        ],
    )[0]
    return str(watcher.watcher_id), str(source.source_folder_id), str(destination.destination_folder_id)


def _create_file(db_session, watcher_id: str, source_folder_id: str) -> str:
    files = FileRepository(db_session)
    file_record = files.create_file_record(
        file_id=generate_uuid(),
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path="/safe/source/inbox/example.csv",
        source_container_locator="/data/sources/inbox/example.csv",
        file_name="example.csv",
        file_extension=".csv",
        size_bytes=128,
        deduplication_key="watcher-alpha:example.csv:128",
        first_seen_at=_ts(8),
        stable_at=_ts(8),
        sha256="a" * 64,
    )
    return str(file_record.file_id)


def test_job_repository_create_get_update_state(db_session) -> None:
    watcher_id, source_folder_id, _destination_folder_id = _create_watcher_graph(db_session)
    file_id = _create_file(db_session, watcher_id, source_folder_id)

    jobs = JobRepository(db_session)
    job = jobs.create_job(
        job_id=generate_uuid(),
        file_id=file_id,
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path="/safe/source/inbox/example.csv",
        source_container_locator="/data/sources/inbox/example.csv",
        source_file_name="example.csv",
        source_extension=".csv",
        source_size_bytes=128,
        source_sha256="a" * 64,
        detected_at=_ts(8),
        stable_at=_ts(8),
        correlation_id=generate_uuid(),
        state="REGISTERED",
    )

    loaded = jobs.get_job(job.job_id)
    assert loaded is not None
    assert loaded.state == "REGISTERED"

    jobs.update_state(job.job_id, new_state="VALIDATING")
    updated = jobs.get_job(job.job_id)
    assert updated is not None
    assert updated.state == "VALIDATING"
    assert updated.terminal_state is None


def test_job_state_history_append(db_session) -> None:
    watcher_id, source_folder_id, _destination_folder_id = _create_watcher_graph(db_session)
    file_id = _create_file(db_session, watcher_id, source_folder_id)
    correlation_id = generate_uuid()

    jobs = JobRepository(db_session)
    job = jobs.create_job(
        job_id=generate_uuid(),
        file_id=file_id,
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path="/safe/source/inbox/example.csv",
        source_container_locator="/data/sources/inbox/example.csv",
        source_file_name="example.csv",
        source_extension=".csv",
        source_size_bytes=128,
        source_sha256="a" * 64,
        detected_at=_ts(8),
        stable_at=_ts(8),
        correlation_id=correlation_id,
        state="REGISTERED",
    )

    jobs.update_state(job.job_id, new_state="VALIDATING")
    history = jobs.append_state_history(
        job_id=job.job_id,
        previous_state="REGISTERED",
        new_state="VALIDATING",
        actor_service="validator",
        reason_code="VALIDATION_STARTED",
        correlation_id=correlation_id,
        transitioned_at=_ts(9),
        event_id=generate_uuid(),
    )

    rows = jobs.list_state_history(job.job_id)
    assert len(rows) == 1
    assert rows[0].transition_sequence == 1
    assert history.new_state == "VALIDATING"
    assert jobs.get_job(job.job_id).state == rows[-1].new_state
