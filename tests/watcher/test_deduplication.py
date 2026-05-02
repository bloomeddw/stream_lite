from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.watchers import WatcherRepository
from app.watcher.deduplication import (
    DUPLICATE_SUPPRESSED,
    check_duplicate,
    compute_deduplication_key,
    record_duplicate_observation,
)


def test_duplicate_key_is_deterministic_and_sensitive_to_documented_fields() -> None:
    watcher_id = uuid4()
    source_folder_id = uuid4()
    key = compute_deduplication_key(watcher_id, source_folder_id, "/source/a.csv", 10, "a" * 64)

    assert key == compute_deduplication_key(watcher_id, source_folder_id, "/source/a.csv", 10, "A" * 64)
    assert key != compute_deduplication_key(watcher_id, source_folder_id, "/source/b.csv", 10, "a" * 64)
    assert len(key) == 64


def test_duplicate_check_and_observation_round_trip(db_session) -> None:
    watcher_repository = WatcherRepository(db_session)
    watcher = watcher_repository.create_watcher(
        name="watcher-dedup",
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
                "display_path": "/source",
                "normalized_path": "/data/sources/source",
                "route_tags": ["A"],
                "route_tags_text": "A",
                "health_status": "green",
                "reason_code": None,
            },
        ],
    )[0]
    watcher_id = watcher.watcher_id
    source_folder_id = source.source_folder_id
    file_id = uuid4()
    job_id = uuid4()
    key = compute_deduplication_key(watcher_id, source_folder_id, "/source/a.csv", 10, "a" * 64)
    file_repository = FileRepository(db_session)
    job_repository = JobRepository(db_session)

    assert not check_duplicate(file_repository, job_repository, deduplication_key=key).is_duplicate

    file_repository.create_file_record(
        file_id=file_id,
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path="/source/a.csv",
        source_container_locator="/tmp/source/a.csv",
        file_name="a.csv",
        file_extension=".csv",
        size_bytes=10,
        deduplication_key=key,
        first_seen_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        stable_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        sha256="a" * 64,
    )
    job_repository.create_job(
        job_id=job_id,
        file_id=file_id,
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path="/source/a.csv",
        source_container_locator="/tmp/source/a.csv",
        source_file_name="a.csv",
        source_extension=".csv",
        source_size_bytes=10,
        detected_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        stable_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        correlation_id=uuid4(),
        state="REGISTERED",
        source_sha256="a" * 64,
    )

    duplicate = check_duplicate(file_repository, job_repository, deduplication_key=key)
    assert duplicate.is_duplicate
    assert duplicate.existing_job_id == job_id

    record_duplicate_observation(
        file_repository,
        existing_job_id=job_id,
        watcher_id=watcher_id,
        source_folder_id=source_folder_id,
        source_display_path="/source/a.csv",
        byte_size=10,
        content_hash="a" * 64,
        observed_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )
    observation = file_repository.list_duplicate_observations(existing_job_id=job_id)[0]
    assert observation.reason_code == DUPLICATE_SUPPRESSED
    assert observation.source_display_path == "/source/a.csv"
    assert observation.content_hash == "a" * 64
