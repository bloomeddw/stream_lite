from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import generate_uuid
from app.repositories.files import FileRepository
from app.repositories.jobs import JobRepository
from app.repositories.stage_claims import StageClaimRepository
from app.repositories.watchers import WatcherRepository


def _seed_job(db_session) -> str:
    watchers = WatcherRepository(db_session)
    watcher = watchers.create_watcher(
        watcher_id=generate_uuid(),
        name="claim-watcher",
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
                "display_path": "/safe/source/claim",
                "normalized_path": "/data/sources/claim",
                "route_tags": ["ALPHA"],
                "route_tags_text": "ALPHA",
                "health_status": "green",
            },
        ],
    )[0]

    files = FileRepository(db_session)
    file_record = files.create_file_record(
        file_id=generate_uuid(),
        watcher_id=watcher.watcher_id,
        source_folder_id=source.source_folder_id,
        source_display_path="/safe/source/claim/file.txt",
        source_container_locator="/data/sources/claim/file.txt",
        file_name="file.txt",
        file_extension=".txt",
        size_bytes=64,
        deduplication_key="claim:file.txt:64",
        first_seen_at=datetime(2026, 4, 30, 8, 0, 0, tzinfo=timezone.utc),
    )

    jobs = JobRepository(db_session)
    job = jobs.create_job(
        job_id=generate_uuid(),
        file_id=file_record.file_id,
        watcher_id=watcher.watcher_id,
        source_folder_id=source.source_folder_id,
        source_display_path="/safe/source/claim/file.txt",
        source_container_locator="/data/sources/claim/file.txt",
        source_file_name="file.txt",
        source_extension=".txt",
        source_size_bytes=64,
        detected_at=datetime(2026, 4, 30, 8, 0, 0, tzinfo=timezone.utc),
        correlation_id=generate_uuid(),
        state="VALIDATED",
    )
    return str(job.job_id)


def test_stage_claim_create_release(db_session) -> None:
    repo = StageClaimRepository(db_session)
    job_id = _seed_job(db_session)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    claim = repo.claim_stage(
        claim_id=generate_uuid(),
        job_id=job_id,
        stage="processing",
        attempt_number=1,
        owner_service="processor",
        lease_expires_at=expires_at,
        correlation_id=generate_uuid(),
    )
    assert claim.claim_status == "active"
    assert claim.lease_expires_at == expires_at

    released = repo.release_stage(claim.claim_id)
    assert released.claim_status == "released"
    assert released.released_at is not None
